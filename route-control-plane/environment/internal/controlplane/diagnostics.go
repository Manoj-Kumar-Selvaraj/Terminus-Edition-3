package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
    "strings"
    "time"
)

type DiagnosticCheck struct {
    NodeID string `json:"node_id,omitempty"`
    Name string `json:"name"`
    Status string `json:"status"`
    Message string `json:"message"`
    Objects []string `json:"objects,omitempty"`
}

type DiagnosticsReport struct {
    Revision uint64 `json:"revision"`
    GeneratedAt time.Time `json:"generated_at"`
    Checks []DiagnosticCheck `json:"checks"`
    Passed int `json:"passed"`
    Warned int `json:"warned"`
    Failed int `json:"failed"`
    Healthy bool `json:"healthy"`
}

type PathProbe struct {
    NodeID string `json:"node_id"`
    Destination string `json:"destination"`
    Reachable bool `json:"reachable"`
    Table int `json:"table"`
    RouteID string `json:"route_id,omitempty"`
    RuleID string `json:"rule_id,omitempty"`
    Reasons []string `json:"reasons"`
}

type PathMatrix struct {
    Revision uint64 `json:"revision"`
    Destinations []string `json:"destinations"`
    Probes []PathProbe `json:"probes"`
    Reachable int `json:"reachable"`
    Unreachable int `json:"unreachable"`
}

func (c *ControlPlane) Diagnostics(nodeID string) DiagnosticsReport {
    c.mu.RLock()
    defer c.mu.RUnlock()
    report:=DiagnosticsReport{Revision:c.desired.Revision,GeneratedAt:time.Now().UTC(),Healthy:true}
    ids:=make([]string,0,len(c.nodes))
    for id:=range c.nodes { if nodeID=="" || id==nodeID { ids=append(ids,id) } }
    sort.Strings(ids)
    for _,id:=range ids {
        node:=c.nodes[id]
        report.Checks=append(report.Checks,diagnosticNodeOnline(node))
        report.Checks=append(report.Checks,diagnosticHeartbeat(node))
        report.Checks=append(report.Checks,c.diagnosticManagementLocked(id,node))
        report.Checks=append(report.Checks,c.diagnosticObservedRevisionLocked(id))
        report.Checks=append(report.Checks,c.diagnosticRouteTablesLocked(id)...)
        report.Checks=append(report.Checks,c.diagnosticRuleTablesLocked(id)...)
        report.Checks=append(report.Checks,c.diagnosticLinksLocked(id)...)
    }
    audit:=c.auditIntegrityLocked()
    status:="pass"; message:="audit sequence is strictly increasing"
    if !audit.StrictlyIncreasing { status="fail"; message="audit sequence is not strictly increasing" }
    report.Checks=append(report.Checks,DiagnosticCheck{Name:"audit.sequence",Status:status,Message:message})
    recovery:=c.recoveryPlanLocked()
    rStatus:="pass"; rMessage:="no unsafe recovery actions are pending"
    if recovery.Blocking { rStatus="fail"; rMessage="recovery plan contains blocking actions" } else if len(recovery.Actions)>0 { rStatus="warn"; rMessage="terminal recovery actions are available" }
    report.Checks=append(report.Checks,DiagnosticCheck{Name:"transactions.recovery",Status:rStatus,Message:rMessage})
    sort.SliceStable(report.Checks,func(i,j int) bool {
        if report.Checks[i].NodeID!=report.Checks[j].NodeID { return report.Checks[i].NodeID<report.Checks[j].NodeID }
        return report.Checks[i].Name<report.Checks[j].Name
    })
    for _,check:=range report.Checks {
        switch check.Status { case "pass": report.Passed++; case "warn": report.Warned++; default: report.Failed++; report.Healthy=false }
    }
    return report
}

func diagnosticNodeOnline(node Node) DiagnosticCheck {
    if node.Online { return DiagnosticCheck{NodeID:node.ID,Name:"node.online",Status:"pass",Message:"node is online"} }
    return DiagnosticCheck{NodeID:node.ID,Name:"node.online",Status:"fail",Message:"node is administratively offline"}
}

func diagnosticHeartbeat(node Node) DiagnosticCheck {
    if node.HeartbeatAt.IsZero() { return DiagnosticCheck{NodeID:node.ID,Name:"node.heartbeat",Status:"warn",Message:"node has no heartbeat timestamp"} }
    age:=time.Since(node.HeartbeatAt)
    if age>5*time.Minute { return DiagnosticCheck{NodeID:node.ID,Name:"node.heartbeat",Status:"fail",Message:fmt.Sprintf("heartbeat is stale by %s",age.Round(time.Second))} }
    if age>2*time.Minute { return DiagnosticCheck{NodeID:node.ID,Name:"node.heartbeat",Status:"warn",Message:fmt.Sprintf("heartbeat is aging: %s",age.Round(time.Second))} }
    return DiagnosticCheck{NodeID:node.ID,Name:"node.heartbeat",Status:"pass",Message:"heartbeat is fresh"}
}

func (c *ControlPlane) diagnosticManagementLocked(id string,node Node) DiagnosticCheck {
    mgmt,err:=canonicalAddress(node.ManagementIP)
    if err!=nil { return DiagnosticCheck{NodeID:id,Name:"management.path",Status:"fail",Message:err.Error()} }
    decision,err:=traceState(c.desired,c.nodes,TraceRequest{NodeID:id,Source:mgmt,Destination:mgmt})
    if err!=nil { return DiagnosticCheck{NodeID:id,Name:"management.path",Status:"fail",Message:err.Error()} }
    if !decision.Reachable { return DiagnosticCheck{NodeID:id,Name:"management.path",Status:"fail",Message:"management address has no reachable route",Objects:decision.Reasons} }
    objects:=[]string{}
    if decision.Route!=nil { objects=append(objects,"route:"+decision.Route.ID) }
    if decision.MatchedRule!=nil { objects=append(objects,"rule:"+decision.MatchedRule.ID) }
    return DiagnosticCheck{NodeID:id,Name:"management.path",Status:"pass",Message:"management address has a usable route",Objects:objects}
}

func (c *ControlPlane) diagnosticObservedRevisionLocked(id string) DiagnosticCheck {
    observed,ok:=c.observed[id]
    if !ok { return DiagnosticCheck{NodeID:id,Name:"observed.revision",Status:"warn",Message:"node has no observed snapshot"} }
    if observed.Revision!=c.desired.Revision { return DiagnosticCheck{NodeID:id,Name:"observed.revision",Status:"warn",Message:fmt.Sprintf("observed revision %d differs from desired %d",observed.Revision,c.desired.Revision)} }
    return DiagnosticCheck{NodeID:id,Name:"observed.revision",Status:"pass",Message:"observed and desired revisions match"}
}

func (c *ControlPlane) diagnosticRouteTablesLocked(id string) []DiagnosticCheck {
    tables:=map[int][]Route{}
    for _,route:=range c.desired.Routes { if route.NodeID==id { tables[route.Table]=append(tables[route.Table],route) } }
    keys:=make([]int,0,len(tables)); for table:=range tables { keys=append(keys,table) }; sort.Ints(keys)
    out:=[]DiagnosticCheck{}
    for _,table:=range keys {
        routes:=tables[table]; defaults:=0; duplicates:=map[string][]string{}
        for _,route:=range routes {
            normalized,err:=normalizeRoute(route); if err!=nil { continue }
            if normalized.Destination=="0.0.0.0/0" || normalized.Destination=="::/0" { defaults++ }
            duplicates[routeIdentity(normalized)]=append(duplicates[routeIdentity(normalized)],normalized.ID)
        }
        collisions:=[]string{}; for _,ids:=range duplicates { if len(ids)>1 { sort.Strings(ids); collisions=append(collisions,strings.Join(ids,",")) } }; sort.Strings(collisions)
        status:="pass"; message:=fmt.Sprintf("table %d has %d routes",table,len(routes))
        if len(collisions)>0 { status="fail"; message="table has duplicate effective route identities" } else if defaults>2 { status="warn"; message="table contains many default-route candidates" }
        out=append(out,DiagnosticCheck{NodeID:id,Name:fmt.Sprintf("table.%d.routes",table),Status:status,Message:message,Objects:collisions})
    }
    return out
}

func (c *ControlPlane) diagnosticRuleTablesLocked(id string) []DiagnosticCheck {
    existing:=map[int]bool{}; for _,route:=range c.desired.Routes { if route.NodeID==id { existing[route.Table]=true } }
    out:=[]DiagnosticCheck{}
    for _,rule:=range c.desired.Rules {
        if rule.NodeID!=id || rule.Action!="lookup" { continue }
        status:="pass"; message:=fmt.Sprintf("lookup table %d exists",rule.Table)
        if !existing[rule.Table] { status="fail"; message=fmt.Sprintf("lookup table %d is absent",rule.Table) }
        out=append(out,DiagnosticCheck{NodeID:id,Name:"rule.table",Status:status,Message:message,Objects:[]string{rule.ID}})
    }
    return out
}

func (c *ControlPlane) diagnosticLinksLocked(id string) []DiagnosticCheck {
    references:=map[string][]string{}
    for _,route:=range c.desired.Routes { if route.NodeID==id { for _,hop:=range route.NextHops { if hop.Interface!="" { references[hop.Interface]=append(references[hop.Interface],route.ID) } } } }
    out:=[]DiagnosticCheck{}
    for _,link:=range c.desired.Links {
        if link.NodeID!=id { continue }
        status:="pass"; message:="link is up"
        if !link.Up && len(references[link.Name])>0 { status="fail"; message="down link is referenced by desired routes" } else if !link.Up { status="warn"; message="link is down but unused" }
        sort.Strings(references[link.Name]); out=append(out,DiagnosticCheck{NodeID:id,Name:"link."+link.Name,Status:status,Message:message,Objects:references[link.Name]})
    }
    return out
}

func (c *ControlPlane) PathMatrix(destinations []string) (PathMatrix,error) {
    c.mu.RLock(); defer c.mu.RUnlock()
    clean:=[]string{}; seen:=map[string]bool{}
    for _,raw:=range destinations { addr,err:=canonicalAddress(raw); if err!=nil { return PathMatrix{},err }; if addr!="" && !seen[addr] { seen[addr]=true; clean=append(clean,addr) } }
    sort.Strings(clean)
    result:=PathMatrix{Revision:c.desired.Revision,Destinations:clean}
    ids:=make([]string,0,len(c.nodes)); for id:=range c.nodes { ids=append(ids,id) }; sort.Strings(ids)
    for _,id:=range ids {
        node:=c.nodes[id]
        source:=node.ManagementIP
        for _,dest:=range clean {
            decision,err:=traceState(c.desired,c.nodes,TraceRequest{NodeID:id,Source:source,Destination:dest})
            probe:=PathProbe{NodeID:id,Destination:dest,Reasons:[]string{}}
            if err!=nil { probe.Reasons=append(probe.Reasons,err.Error()); result.Unreachable++; result.Probes=append(result.Probes,probe); continue }
            probe.Reachable=decision.Reachable; probe.Table=decision.Table; probe.Reasons=append(probe.Reasons,decision.Reasons...)
            if decision.Route!=nil { probe.RouteID=decision.Route.ID }; if decision.MatchedRule!=nil { probe.RuleID=decision.MatchedRule.ID }
            if probe.Reachable { result.Reachable++ } else { result.Unreachable++ }
            result.Probes=append(result.Probes,probe)
        }
    }
    return result,nil
}

func (c *ControlPlane) auditIntegrityLocked() AuditIntegrityReport {
    report:=AuditIntegrityReport{Events:len(c.audit),StrictlyIncreasing:true}; if len(c.audit)==0 { return report }
    report.FirstSequence=c.audit[0].Sequence; report.LastSequence=c.audit[len(c.audit)-1].Sequence; seen:=map[uint64]bool{}; previous:=uint64(0)
    for i,event:=range c.audit { if seen[event.Sequence] { report.DuplicateSequences=append(report.DuplicateSequences,event.Sequence); report.StrictlyIncreasing=false }; seen[event.Sequence]=true; if i>0 { if event.Sequence<=previous { report.StrictlyIncreasing=false }; if event.Sequence>previous+1 { report.Gaps=append(report.Gaps,fmt.Sprintf("%d-%d",previous+1,event.Sequence-1)) } }; previous=event.Sequence }
    return report
}

func (c *ControlPlane) recoveryPlanLocked() RecoveryPlan {
    plan:=RecoveryPlan{Revision:c.desired.Revision}
    for id,txn:=range c.transactions { if txn.Phase==TransactionPrepared || txn.Phase==TransactionApplying || txn.Phase==TransactionRollingBack { nodes:=[]string{}; for nodeID:=range txn.Nodes { nodes=append(nodes,nodeID) }; sort.Strings(nodes); safe:=txn.Phase!=TransactionRollingBack && txn.TargetRevision>=c.desired.Revision; action:="fail_and_reconcile"; if !safe { action="quarantine"; plan.Blocking=true }; plan.Actions=append(plan.Actions,RecoveryAction{TransactionID:id,Action:action,Safe:safe,Reason:"non-terminal durable transaction",AffectedNodes:nodes}) } }
    for key,id:=range c.idempotency { if _,ok:=c.transactions[id]; !ok { plan.OrphanedIdempotencyKeys=append(plan.OrphanedIdempotencyKeys,key); plan.Blocking=true } }; sort.Strings(plan.OrphanedIdempotencyKeys); return plan
}

func addressFamily(value string) string { addr,err:=netip.ParseAddr(value); if err!=nil { return "unknown" }; if addr.Is6() { return "ipv6" }; return "ipv4" }
