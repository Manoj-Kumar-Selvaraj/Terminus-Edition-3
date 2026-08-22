package controlplane

import (
    "fmt"
    "sort"
    "strings"
)

type ConsistencyIssue struct {
    Scope string `json:"scope"`
    Code string `json:"code"`
    Severity string `json:"severity"`
    Message string `json:"message"`
    Objects []string `json:"objects,omitempty"`
}

type ConsistencyReport struct {
    Revision uint64 `json:"revision"`
    Issues []ConsistencyIssue `json:"issues"`
    Critical int `json:"critical"`
    High int `json:"high"`
    Medium int `json:"medium"`
    Low int `json:"low"`
    Consistent bool `json:"consistent"`
}

func (c *ControlPlane) Consistency() ConsistencyReport {
    c.mu.RLock(); defer c.mu.RUnlock()
    report:=ConsistencyReport{Revision:c.desired.Revision,Consistent:true}
    report.Issues=append(report.Issues,c.consistencyNodesLocked()...)
    report.Issues=append(report.Issues,c.consistencyRoutesLocked()...)
    report.Issues=append(report.Issues,c.consistencyRulesLocked()...)
    report.Issues=append(report.Issues,c.consistencyTransactionsLocked()...)
    report.Issues=append(report.Issues,c.consistencyRolloutsLocked()...)
    report.Issues=append(report.Issues,c.consistencyAuditLocked()...)
    sort.Slice(report.Issues,func(i,j int) bool { if report.Issues[i].Severity!=report.Issues[j].Severity { return severityRank(report.Issues[i].Severity)>severityRank(report.Issues[j].Severity) }; if report.Issues[i].Scope!=report.Issues[j].Scope { return report.Issues[i].Scope<report.Issues[j].Scope }; return report.Issues[i].Code<report.Issues[j].Code })
    for _,issue:=range report.Issues { switch issue.Severity { case "critical": report.Critical++; report.Consistent=false; case "high": report.High++; report.Consistent=false; case "medium": report.Medium++; case "low": report.Low++ } }
    return report
}

func (c *ControlPlane) consistencyNodesLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}; hostnames:=map[string][]string{}; addresses:=map[string][]string{}
    for id,node:=range c.nodes { hostnames[strings.ToLower(strings.TrimSpace(node.Hostname))]=append(hostnames[strings.ToLower(strings.TrimSpace(node.Hostname))],id); if canonical,err:=canonicalAddress(node.ManagementIP); err==nil { addresses[canonical]=append(addresses[canonical],id) } else { out=append(out,ConsistencyIssue{Scope:"node:"+id,Code:"INVALID_MANAGEMENT_IP",Severity:"critical",Message:err.Error()}) } }
    for hostname,ids:=range hostnames { if hostname!="" && len(ids)>1 { sort.Strings(ids); out=append(out,ConsistencyIssue{Scope:"fleet",Code:"DUPLICATE_HOSTNAME",Severity:"high",Message:"multiple nodes share a hostname",Objects:ids}) } }
    for address,ids:=range addresses { if len(ids)>1 { sort.Strings(ids); out=append(out,ConsistencyIssue{Scope:"fleet",Code:"DUPLICATE_MANAGEMENT_IP",Severity:"critical",Message:"multiple nodes share management address "+address,Objects:ids}) } }
    return out
}

func (c *ControlPlane) consistencyRoutesLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}; identities:=map[string][]string{}; ids:=map[string][]string{}
    for _,raw:=range c.desired.Routes {
        route,err:=normalizeRoute(raw); if err!=nil { out=append(out,ConsistencyIssue{Scope:"route:"+raw.ID,Code:"INVALID_ROUTE",Severity:"high",Message:err.Error()}); continue }
        ids[route.ID]=append(ids[route.ID],route.NodeID); identities[routeIdentity(route)]=append(identities[routeIdentity(route)],route.ID)
        if _,ok:=c.nodes[route.NodeID]; !ok { out=append(out,ConsistencyIssue{Scope:"route:"+route.ID,Code:"UNKNOWN_NODE",Severity:"critical",Message:"route references an unknown node",Objects:[]string{route.NodeID}}) }
        if route.Table<=0 { out=append(out,ConsistencyIssue{Scope:"route:"+route.ID,Code:"INVALID_TABLE",Severity:"high",Message:"route table must be positive"}) }
    }
    for id,nodes:=range ids { if id!="" && len(nodes)>1 { sort.Strings(nodes); out=append(out,ConsistencyIssue{Scope:"routes",Code:"DUPLICATE_ROUTE_ID",Severity:"high",Message:"route id occurs more than once: "+id,Objects:nodes}) } }
    for _,routeIDs:=range identities { if len(routeIDs)>1 { sort.Strings(routeIDs); out=append(out,ConsistencyIssue{Scope:"routes",Code:"DUPLICATE_EFFECTIVE_ROUTE",Severity:"high",Message:"routes share canonical forwarding identity",Objects:routeIDs}) } }
    return out
}

func (c *ControlPlane) consistencyRulesLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}; priorities:=map[string][]string{}; tables:=map[string]bool{}
    for _,route:=range c.desired.Routes { tables[fmt.Sprintf("%s|%d",route.NodeID,route.Table)]=true }
    for _,raw:=range c.desired.Rules {
        rule,err:=normalizeRule(raw); if err!=nil { out=append(out,ConsistencyIssue{Scope:"rule:"+raw.ID,Code:"INVALID_RULE",Severity:"high",Message:err.Error()}); continue }
        key:=fmt.Sprintf("%s|%s|%d",rule.NodeID,rule.Family,rule.Priority); priorities[key]=append(priorities[key],rule.ID)
        if _,ok:=c.nodes[rule.NodeID]; !ok { out=append(out,ConsistencyIssue{Scope:"rule:"+rule.ID,Code:"UNKNOWN_NODE",Severity:"critical",Message:"rule references an unknown node"}) }
        if rule.Action=="lookup" && !tables[fmt.Sprintf("%s|%d",rule.NodeID,rule.Table)] { out=append(out,ConsistencyIssue{Scope:"rule:"+rule.ID,Code:"MISSING_TABLE",Severity:"critical",Message:"lookup rule references a table with no desired routes"}) }
    }
    for _,ruleIDs:=range priorities { if len(ruleIDs)>1 { sort.Strings(ruleIDs); out=append(out,ConsistencyIssue{Scope:"rules",Code:"PRIORITY_COLLISION",Severity:"high",Message:"multiple rules compete at one effective priority",Objects:ruleIDs}) } }
    return out
}

func (c *ControlPlane) consistencyTransactionsLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}
    for id,txn:=range c.transactions {
        if txn.TargetRevision<txn.BaseRevision { out=append(out,ConsistencyIssue{Scope:"transaction:"+id,Code:"REVISION_REGRESSION",Severity:"critical",Message:"transaction target revision is older than base revision"}) }
        if mapped,ok:=c.idempotency[txn.IdempotencyKey]; txn.IdempotencyKey!="" && (!ok || mapped!=id) { out=append(out,ConsistencyIssue{Scope:"transaction:"+id,Code:"IDEMPOTENCY_MISMATCH",Severity:"high",Message:"transaction idempotency mapping is missing or points elsewhere"}) }
        for nodeID,nodeTxn:=range txn.Nodes { if nodeTxn.NodeID!=nodeID { out=append(out,ConsistencyIssue{Scope:"transaction:"+id,Code:"NODE_KEY_MISMATCH",Severity:"medium",Message:"node transaction key disagrees with embedded node id",Objects:[]string{nodeID,nodeTxn.NodeID}}) } }
    }
    for key,id:=range c.idempotency { if _,ok:=c.transactions[id]; !ok { out=append(out,ConsistencyIssue{Scope:"idempotency:"+key,Code:"ORPHAN_MAPPING",Severity:"high",Message:"idempotency key points to absent transaction",Objects:[]string{id}}) } }
    return out
}

func (c *ControlPlane) consistencyRolloutsLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}
    for id,rollout:=range c.rollouts {
        if rollout.Revision>c.desired.Revision { out=append(out,ConsistencyIssue{Scope:"rollout:"+id,Code:"FUTURE_REVISION",Severity:"critical",Message:"rollout references a revision newer than desired state"}) }
        seen:=map[string]bool{}
        for _,wave:=range rollout.Waves { for _,node:=range wave.Nodes { if seen[node.NodeID] { out=append(out,ConsistencyIssue{Scope:"rollout:"+id,Code:"DUPLICATE_NODE",Severity:"high",Message:"node appears in multiple rollout waves",Objects:[]string{node.NodeID}}) }; seen[node.NodeID]=true } }
    }
    return out
}

func (c *ControlPlane) consistencyAuditLocked() []ConsistencyIssue {
    out:=[]ConsistencyIssue{}; previous:=uint64(0)
    for i,event:=range c.audit { if i>0 && event.Sequence<=previous { out=append(out,ConsistencyIssue{Scope:"audit",Code:"NON_MONOTONIC_SEQUENCE",Severity:"critical",Message:fmt.Sprintf("sequence %d follows %d",event.Sequence,previous)}) }; previous=event.Sequence }
    if len(c.audit)>0 && c.sequence<c.audit[len(c.audit)-1].Sequence { out=append(out,ConsistencyIssue{Scope:"audit",Code:"COUNTER_BEHIND",Severity:"critical",Message:"durable audit counter is behind last event"}) }
    return out
}
