package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
    "strings"
)

type SafetyViolation struct {
    NodeID string `json:"node_id"`
    Code string `json:"code"`
    Severity string `json:"severity"`
    Message string `json:"message"`
    ObjectID string `json:"object_id,omitempty"`
}

type SafetyReport struct {
    BaseRevision uint64 `json:"base_revision"`
    CandidateRevision uint64 `json:"candidate_revision"`
    Safe bool `json:"safe"`
    Violations []SafetyViolation `json:"violations"`
    ProtectedPaths []string `json:"protected_paths"`
    TouchedNodes []string `json:"touched_nodes"`
}

func (c *ControlPlane) CheckSafety(req ChangeRequest) (SafetyReport, error) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    if req.BaseRevision != c.desired.Revision {
        return SafetyReport{}, fmt.Errorf("%w: base revision %d does not match current %d",ErrConflict,req.BaseRevision,c.desired.Revision)
    }
    candidate := cloneDesired(c.desired)
    if err:=applyRouteMutations(&candidate,req.RouteMutations); err!=nil { return SafetyReport{},err }
    if err:=applyRuleMutations(&candidate,req.RuleMutations); err!=nil { return SafetyReport{},err }
    candidate.Revision = c.desired.Revision+1
    if err:=validateDesired(candidate,c.nodes); err!=nil { return SafetyReport{},err }
    report:=SafetyReport{BaseRevision:req.BaseRevision,CandidateRevision:candidate.Revision,Safe:true}
    touched:=map[string]bool{}
    for _, mutation:=range req.RouteMutations { if mutation.Route.NodeID!="" { touched[mutation.Route.NodeID]=true } }
    for _, mutation:=range req.RuleMutations { if mutation.Rule.NodeID!="" { touched[mutation.Rule.NodeID]=true } }
    for id:=range touched { report.TouchedNodes=append(report.TouchedNodes,id) }
    sort.Strings(report.TouchedNodes)
    for nodeID,node:=range c.nodes {
        management, err:=canonicalAddress(node.ManagementIP)
        if err!=nil { return SafetyReport{},err }
        decision, traceErr:=traceState(candidate,c.nodes,TraceRequest{NodeID:nodeID,Source:management,Destination:management})
        if traceErr!=nil || !decision.Reachable {
            report.Violations=append(report.Violations,SafetyViolation{NodeID:nodeID,Code:"MANAGEMENT_UNREACHABLE",Severity:"critical",Message:"candidate state removes a usable path to the node management address"})
            continue
        }
        if decision.Route!=nil { report.ProtectedPaths=append(report.ProtectedPaths,nodeID+":"+decision.Route.Destination) }
        for _, cidr:=range c.cfg.ProtectedCIDRs {
            prefix, parseErr:=netip.ParsePrefix(strings.TrimSpace(cidr))
            if parseErr!=nil { continue }
            mgmtAddr, parseErr:=netip.ParseAddr(management)
            if parseErr==nil && prefix.Contains(mgmtAddr) && decision.Route!=nil && decision.Route.Type=="blackhole" {
                report.Violations=append(report.Violations,SafetyViolation{NodeID:nodeID,Code:"PROTECTED_BLACKHOLE",Severity:"critical",Message:"protected management address resolves to a blackhole route",ObjectID:decision.Route.ID})
            }
        }
    }
    report.Violations=append(report.Violations,validateCandidateLinks(candidate)...)
    report.Violations=append(report.Violations,validateCandidateGateways(candidate)...)
    sort.Slice(report.Violations,func(i,j int) bool {
        if report.Violations[i].NodeID!=report.Violations[j].NodeID { return report.Violations[i].NodeID<report.Violations[j].NodeID }
        if report.Violations[i].Severity!=report.Violations[j].Severity { return report.Violations[i].Severity<report.Violations[j].Severity }
        return report.Violations[i].Code<report.Violations[j].Code
    })
    sort.Strings(report.ProtectedPaths)
    for _, v:=range report.Violations { if v.Severity=="critical" || v.Severity=="high" { report.Safe=false; break } }
    return report,nil
}

func validateCandidateLinks(state DesiredState) []SafetyViolation {
    linkState:=map[string]Link{}
    for _, link:=range state.Links { linkState[link.NodeID+"|"+link.Name]=link }
    out:=[]SafetyViolation{}
    for _, route:=range state.Routes {
        if route.Type=="blackhole" || route.Type=="unreachable" || route.Type=="prohibit" { continue }
        for _, hop:=range route.NextHops {
            if hop.Interface=="" { continue }
            link,ok:=linkState[route.NodeID+"|"+hop.Interface]
            if !ok {
                out=append(out,SafetyViolation{NodeID:route.NodeID,Code:"MISSING_LINK",Severity:"high",Message:"route references an interface that is not present in desired topology",ObjectID:route.ID})
                continue
            }
            if !link.Up { out=append(out,SafetyViolation{NodeID:route.NodeID,Code:"DOWN_LINK",Severity:"high",Message:"route depends on an administratively down link",ObjectID:route.ID}) }
        }
    }
    return out
}

func validateCandidateGateways(state DesiredState) []SafetyViolation {
    out:=[]SafetyViolation{}
    for _, route:=range state.Routes {
        for _, hop:=range route.NextHops {
            if hop.Gateway=="" || hop.Interface=="" { continue }
            if !gatewayOnLink(state.Links,route.NodeID,hop.Interface,hop.Gateway) {
                out=append(out,SafetyViolation{NodeID:route.NodeID,Code:"GATEWAY_OFFLINK",Severity:"high",Message:"next-hop gateway is not reachable through the selected link",ObjectID:route.ID})
            }
        }
    }
    return out
}

func (c *ControlPlane) ManagementReachability() []SafetyViolation {
    c.mu.RLock()
    defer c.mu.RUnlock()
    out:=[]SafetyViolation{}
    for nodeID,node:=range c.nodes {
        address,err:=canonicalAddress(node.ManagementIP)
        if err!=nil { out=append(out,SafetyViolation{NodeID:nodeID,Code:"INVALID_MANAGEMENT_ADDRESS",Severity:"critical",Message:err.Error()}); continue }
        decision,err:=traceState(c.desired,c.nodes,TraceRequest{NodeID:nodeID,Source:address,Destination:address})
        if err!=nil || !decision.Reachable { out=append(out,SafetyViolation{NodeID:nodeID,Code:"MANAGEMENT_UNREACHABLE",Severity:"critical",Message:"current desired state has no usable management path"}) }
    }
    sort.Slice(out,func(i,j int) bool { return out[i].NodeID<out[j].NodeID })
    return out
}
