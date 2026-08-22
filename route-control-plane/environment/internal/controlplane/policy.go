package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
    "strings"
)

type PolicyFinding struct {
    NodeID string `json:"node_id"`
    Severity string `json:"severity"`
    Code string `json:"code"`
    ObjectType string `json:"object_type"`
    ObjectID string `json:"object_id"`
    Message string `json:"message"`
}

type PolicyReport struct {
    Revision uint64 `json:"revision"`
    NodeID string `json:"node_id,omitempty"`
    Passed bool `json:"passed"`
    Findings []PolicyFinding `json:"findings"`
    Summary map[string]int `json:"summary"`
}

func (c *ControlPlane) EvaluatePolicy(nodeID string) PolicyReport {
    c.mu.RLock()
    defer c.mu.RUnlock()
    report:=PolicyReport{Revision:c.desired.Revision,NodeID:nodeID,Passed:true,Summary:map[string]int{}}
    linkByNode:=map[string]map[string]Link{}
    for _,link:=range c.desired.Links {
        if linkByNode[link.NodeID]==nil { linkByNode[link.NodeID]=map[string]Link{} }
        linkByNode[link.NodeID][link.Name]=link
    }
    tableRules:=map[string]int{}
    for _,rule:=range c.desired.Rules {
        if nodeID!="" && rule.NodeID!=nodeID { continue }
        if rule.Action=="lookup" { tableRules[fmt.Sprintf("%s|%d",rule.NodeID,rule.Table)]++ }
        if rule.Priority<0 {
            report.Findings=append(report.Findings,PolicyFinding{NodeID:rule.NodeID,Severity:"high",Code:"NEGATIVE_RULE_PRIORITY",ObjectType:"rule",ObjectID:rule.ID,Message:"policy rule priority must be non-negative"})
        }
        if rule.Action!="lookup" && rule.Action!="blackhole" && rule.Action!="unreachable" && rule.Action!="prohibit" {
            report.Findings=append(report.Findings,PolicyFinding{NodeID:rule.NodeID,Severity:"medium",Code:"UNKNOWN_RULE_ACTION",ObjectType:"rule",ObjectID:rule.ID,Message:"policy rule uses an unrecognized action"})
        }
    }
    for _,route:=range c.desired.Routes {
        if nodeID!="" && route.NodeID!=nodeID { continue }
        if route.Owner=="" { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"medium",Code:"UNOWNED_DESIRED_ROUTE",ObjectType:"route",ObjectID:route.ID,Message:"desired route does not declare an owner"}) }
        if route.Metric<0 { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"high",Code:"NEGATIVE_METRIC",ObjectType:"route",ObjectID:route.ID,Message:"route metric cannot be negative"}) }
        if len(route.NextHops)>8 { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"medium",Code:"EXCESSIVE_ECMP_WIDTH",ObjectType:"route",ObjectID:route.ID,Message:"multipath route exceeds recommended next-hop width"}) }
        if route.Type=="unicast" && len(route.NextHops)==0 { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"high",Code:"UNICAST_WITHOUT_NEXTHOP",ObjectType:"route",ObjectID:route.ID,Message:"unicast route has no forwarding next hop"}) }
        for _,hop:=range route.NextHops {
            if hop.Interface=="" { continue }
            link,ok:=linkByNode[route.NodeID][hop.Interface]
            if !ok { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"high",Code:"UNKNOWN_INTERFACE",ObjectType:"route",ObjectID:route.ID,Message:"route references an interface absent from topology"}); continue }
            if !link.Up { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"high",Code:"DOWN_INTERFACE",ObjectType:"route",ObjectID:route.ID,Message:"route depends on a down interface"}) }
            if hop.Gateway!="" {
                gw,err:=netip.ParseAddr(hop.Gateway)
                if err==nil {
                    compatible:=false
                    for _,raw:=range link.Addresses { if p,e:=netip.ParsePrefix(raw); e==nil && p.Addr().BitLen()==gw.BitLen() { compatible=true; break } }
                    if !compatible { report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"high",Code:"GATEWAY_FAMILY_MISMATCH",ObjectType:"route",ObjectID:route.ID,Message:"gateway address family is not configured on selected link"}) }
                }
            }
        }
        if route.Protocol=="kernel" && normalizeOwner(route.Owner)=="routecp" {
            report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"medium",Code:"KERNEL_PROTOCOL_OWNERSHIP",ObjectType:"route",ObjectID:route.ID,Message:"routecp-managed desired routes should not claim kernel protocol ownership"})
        }
        if route.Table!=254 && tableRules[fmt.Sprintf("%s|%d",route.NodeID,route.Table)]==0 {
            report.Findings=append(report.Findings,PolicyFinding{NodeID:route.NodeID,Severity:"low",Code:"UNREFERENCED_TABLE",ObjectType:"route",ObjectID:route.ID,Message:"non-main table is not referenced by any lookup rule"})
        }
    }
    report.Findings=append(report.Findings,c.policyManagementFindingsLocked(nodeID)...)
    sort.Slice(report.Findings,func(i,j int) bool {
        if report.Findings[i].NodeID!=report.Findings[j].NodeID { return report.Findings[i].NodeID<report.Findings[j].NodeID }
        if report.Findings[i].Severity!=report.Findings[j].Severity { return severityRank(report.Findings[i].Severity)>severityRank(report.Findings[j].Severity) }
        if report.Findings[i].Code!=report.Findings[j].Code { return report.Findings[i].Code<report.Findings[j].Code }
        return report.Findings[i].ObjectID<report.Findings[j].ObjectID
    })
    for _,f:=range report.Findings { report.Summary[f.Severity]++; if f.Severity=="critical" || f.Severity=="high" { report.Passed=false } }
    return report
}

func (c *ControlPlane) policyManagementFindingsLocked(nodeID string) []PolicyFinding {
    out:=[]PolicyFinding{}
    for id,node:=range c.nodes {
        if nodeID!="" && id!=nodeID { continue }
        mgmt,err:=canonicalAddress(node.ManagementIP)
        if err!=nil { out=append(out,PolicyFinding{NodeID:id,Severity:"critical",Code:"INVALID_MANAGEMENT_IP",ObjectType:"node",ObjectID:id,Message:err.Error()}); continue }
        decision,err:=traceState(c.desired,c.nodes,TraceRequest{NodeID:id,Source:mgmt,Destination:mgmt})
        if err!=nil || !decision.Reachable { out=append(out,PolicyFinding{NodeID:id,Severity:"critical",Code:"MANAGEMENT_PATH_MISSING",ObjectType:"node",ObjectID:id,Message:"management address has no usable forwarding path"}) }
    }
    return out
}

func severityRank(value string) int {
    switch strings.ToLower(value) { case "critical": return 4; case "high": return 3; case "medium": return 2; case "low": return 1; default: return 0 }
}
