package controlplane

import (
    "fmt"
    "sort"
)

type ChangeImpactRequest struct {
    Change ChangeRequest `json:"change"`
    RolloutSelector map[string]string `json:"rollout_selector"`
    WaveSize int `json:"wave_size"`
}

type NodeImpact struct {
    NodeID string `json:"node_id"`
    AddedRoutes int `json:"added_routes"`
    RemovedRoutes int `json:"removed_routes"`
    ChangedRoutes int `json:"changed_routes"`
    AddedRules int `json:"added_rules"`
    RemovedRules int `json:"removed_rules"`
    ChangedRules int `json:"changed_rules"`
    Tables []int `json:"tables"`
    ManagementCritical bool `json:"management_critical"`
    DriftBefore int `json:"drift_before"`
}

type ChangeImpactReport struct {
    BaseRevision uint64 `json:"base_revision"`
    CandidateRevision uint64 `json:"candidate_revision"`
    Nodes []NodeImpact `json:"nodes"`
    TotalObjects int `json:"total_objects"`
    FailureDomains []string `json:"failure_domains"`
    Safety SafetyReport `json:"safety"`
    Rollout *RolloutPreview `json:"rollout,omitempty"`
    Risk string `json:"risk"`
    Reasons []string `json:"reasons"`
}

func (c *ControlPlane) ChangeImpact(req ChangeImpactRequest) (ChangeImpactReport,error) {
    safety,err:=c.CheckSafety(req.Change); if err!=nil { return ChangeImpactReport{},err }
    c.mu.RLock(); defer c.mu.RUnlock()
    candidate:=cloneDesired(c.desired)
    if err:=applyRouteMutations(&candidate,req.Change.RouteMutations); err!=nil { return ChangeImpactReport{},err }
    if err:=applyRuleMutations(&candidate,req.Change.RuleMutations); err!=nil { return ChangeImpactReport{},err }
    candidate.Revision=c.desired.Revision+1
    impact:=ChangeImpactReport{BaseRevision:c.desired.Revision,CandidateRevision:candidate.Revision,Safety:safety,Risk:"low"}
    nodes:=map[string]*NodeImpact{}
    ensure:=func(id string)*NodeImpact { item:=nodes[id]; if item==nil { item=&NodeImpact{NodeID:id}; nodes[id]=item }; return item }
    oldRoutes:=indexRoutes(c.desired.Routes); newRoutes:=indexRoutes(candidate.Routes)
    for key,route:=range oldRoutes {
        item:=ensure(route.NodeID)
        if next,ok:=newRoutes[key]; !ok { item.RemovedRoutes++; item.Tables=appendUniqueInt(item.Tables,route.Table) } else if !routeEquivalent(route,next) { item.ChangedRoutes++; item.Tables=appendUniqueInt(item.Tables,route.Table) }
    }
    for key,route:=range newRoutes { if _,ok:=oldRoutes[key]; !ok { item:=ensure(route.NodeID); item.AddedRoutes++; item.Tables=appendUniqueInt(item.Tables,route.Table) } }
    oldRules:=indexRules(c.desired.Rules); newRules:=indexRules(candidate.Rules)
    for key,rule:=range oldRules {
        item:=ensure(rule.NodeID)
        if next,ok:=newRules[key]; !ok { item.RemovedRules++; item.Tables=appendUniqueInt(item.Tables,rule.Table) } else if !ruleEquivalent(rule,next) { item.ChangedRules++; item.Tables=appendUniqueInt(item.Tables,rule.Table) }
    }
    for key,rule:=range newRules { if _,ok:=oldRules[key]; !ok { item:=ensure(rule.NodeID); item.AddedRules++; item.Tables=appendUniqueInt(item.Tables,rule.Table) } }
    driftCount:=map[string]int{}; for _,d:=range c.driftLocked("") { driftCount[d.NodeID]++ }
    siteSet:=map[string]bool{}
    for id,item:=range nodes {
        sort.Ints(item.Tables); item.DriftBefore=driftCount[id]
        for _,v:=range safety.Violations { if v.NodeID==id && (v.Severity=="critical" || v.Severity=="high") { item.ManagementCritical=true } }
        if node,ok:=c.nodes[id]; ok { siteSet[node.Site]=true }
        impact.TotalObjects+=item.AddedRoutes+item.RemovedRoutes+item.ChangedRoutes+item.AddedRules+item.RemovedRules+item.ChangedRules
        impact.Nodes=append(impact.Nodes,*item)
    }
    sort.Slice(impact.Nodes,func(i,j int) bool { return impact.Nodes[i].NodeID<impact.Nodes[j].NodeID })
    for site:=range siteSet { impact.FailureDomains=append(impact.FailureDomains,site) }; sort.Strings(impact.FailureDomains)
    if !safety.Safe { impact.Risk="blocked"; impact.Reasons=append(impact.Reasons,"candidate violates management or topology safety") }
    if len(impact.FailureDomains)>1 && impact.Risk!="blocked" { impact.Risk="high"; impact.Reasons=append(impact.Reasons,"change crosses multiple failure domains") }
    if impact.TotalObjects>25 && impact.Risk=="low" { impact.Risk="medium"; impact.Reasons=append(impact.Reasons,"large object blast radius") }
    if req.RolloutSelector!=nil {
        selected:=c.selectNodesLocked(req.RolloutSelector)
        if len(selected)>0 {
            preview:=previewRolloutLocked(c,RolloutRequest{Revision:c.desired.Revision,Selector:req.RolloutSelector,WaveSize:req.WaveSize})
            impact.Rollout=&preview
        }
    }
    sort.Strings(impact.Reasons)
    return impact,nil
}

func previewRolloutLocked(c *ControlPlane,req RolloutRequest) RolloutPreview {
    if req.WaveSize<1 { req.WaveSize=5 }
    selected:=c.selectNodesLocked(req.Selector)
    result:=RolloutPreview{Revision:req.Revision,SelectedNodes:append([]string(nil),selected...),Risk:"low"}
    rest:=append([]string(nil),selected...)
    for len(rest)>0 { n:=req.WaveSize; if n>len(rest) { n=len(rest) }; result.Waves=append(result.Waves,append([]string(nil),rest[:n]...)); rest=rest[n:] }
    return result
}

func indexRoutes(routes []Route) map[string]Route { out:=map[string]Route{}; for _,r:=range routes { out[r.ID]=r }; return out }
func indexRules(rules []PolicyRule) map[string]PolicyRule { out:=map[string]PolicyRule{}; for _,r:=range rules { out[r.ID]=r }; return out }
func appendUniqueInt(values []int,value int) []int { for _,v:=range values { if v==value { return values } }; return append(values,value) }

func (c *ControlPlane) ValidateDependencies(nodeID string) []string {
    graph:=c.Dependencies(nodeID); out:=[]string{}
    for _,edge:=range graph.Edges {
        if edge.Critical && edge.To=="" { out=append(out,fmt.Sprintf("%s has empty critical dependency",edge.From)) }
    }
    for _,cycle:=range graph.Cycles { out=append(out,"dependency cycle: "+fmt.Sprint(cycle)) }
    sort.Strings(out); return out
}
