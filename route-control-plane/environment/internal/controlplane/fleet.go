package controlplane

import (
    "fmt"
    "sort"
    "time"
)

type FleetDomainHealth struct {
    Domain string `json:"domain"`
    Nodes int `json:"nodes"`
    Online int `json:"online"`
    StaleHeartbeats int `json:"stale_heartbeats"`
    RevisionSkew int `json:"revision_skew"`
    DriftItems int `json:"drift_items"`
}

type FleetHealth struct {
    Revision uint64 `json:"revision"`
    Nodes int `json:"nodes"`
    Online int `json:"online"`
    Offline int `json:"offline"`
    StaleHeartbeats int `json:"stale_heartbeats"`
    RevisionSkew int `json:"revision_skew"`
    Sites []FleetDomainHealth `json:"sites"`
    Environments []FleetDomainHealth `json:"environments"`
    Healthy bool `json:"healthy"`
}

type RolloutPreview struct {
    Revision uint64 `json:"revision"`
    SelectedNodes []string `json:"selected_nodes"`
    Canaries []string `json:"canaries"`
    Waves [][]string `json:"waves"`
    AlreadyCurrent []string `json:"already_current"`
    Offline []string `json:"offline"`
    StaleHeartbeat []string `json:"stale_heartbeat"`
    Risk string `json:"risk"`
    BlockingReasons []string `json:"blocking_reasons"`
}

func (c *ControlPlane) FleetHealth() FleetHealth {
    c.mu.RLock(); defer c.mu.RUnlock()
    now:=time.Now().UTC(); result:=FleetHealth{Revision:c.desired.Revision,Nodes:len(c.nodes),Healthy:true}
    site:=map[string]*FleetDomainHealth{}; env:=map[string]*FleetDomainHealth{}
    driftByNode:=map[string]int{}
    for _,item:=range c.driftLocked("") { driftByNode[item.NodeID]++ }
    for id,node:=range c.nodes {
        if node.Online { result.Online++ } else { result.Offline++; result.Healthy=false }
        stale:=node.HeartbeatAt.IsZero() || now.Sub(node.HeartbeatAt)>2*time.Minute
        if stale { result.StaleHeartbeats++; result.Healthy=false }
        observed:=c.observed[id]
        skew:=0; if observed.Revision!=c.desired.Revision { skew=1; result.RevisionSkew++; result.Healthy=false }
        addFleetDomain(site,node.Site,node.Online,stale,skew,driftByNode[id])
        addFleetDomain(env,node.Environment,node.Online,stale,skew,driftByNode[id])
    }
    result.Sites=flattenFleetDomains(site); result.Environments=flattenFleetDomains(env)
    return result
}

func addFleetDomain(index map[string]*FleetDomainHealth,key string,online,stale bool,skew,drift int) {
    if key=="" { key="unknown" }
    item:=index[key]; if item==nil { item=&FleetDomainHealth{Domain:key}; index[key]=item }
    item.Nodes++; if online { item.Online++ }; if stale { item.StaleHeartbeats++ }; item.RevisionSkew+=skew; item.DriftItems+=drift
}

func flattenFleetDomains(index map[string]*FleetDomainHealth) []FleetDomainHealth {
    out:=make([]FleetDomainHealth,0,len(index)); for _,item:=range index { out=append(out,*item) }
    sort.Slice(out,func(i,j int) bool { return out[i].Domain<out[j].Domain }); return out
}

func (c *ControlPlane) PreviewRollout(req RolloutRequest) (RolloutPreview,error) {
    c.mu.RLock(); defer c.mu.RUnlock()
    if req.Revision==0 { req.Revision=c.desired.Revision }
    if req.Revision!=c.desired.Revision { return RolloutPreview{},fmt.Errorf("%w: rollout revision %d is not current %d",ErrConflict,req.Revision,c.desired.Revision) }
    if req.WaveSize<1 { req.WaveSize=5 }
    if req.WaveSize>c.cfg.MaxWave { return RolloutPreview{},fmt.Errorf("wave_size %d exceeds maximum %d",req.WaveSize,c.cfg.MaxWave) }
    selected:=c.selectNodesLocked(req.Selector); if len(selected)==0 { return RolloutPreview{},fmt.Errorf("no nodes match selector") }
    result:=RolloutPreview{Revision:req.Revision,SelectedNodes:append([]string(nil),selected...),Canaries:uniqueSorted(req.CanaryNodes),Risk:"low"}
    selectedSet:=map[string]bool{}; for _,id:=range selected { selectedSet[id]=true }
    for _,id:=range result.Canaries { if !selectedSet[id] { result.BlockingReasons=append(result.BlockingReasons,"canary outside selector: "+id) } }
    now:=time.Now().UTC()
    pending:=[]string{}
    for _,id:=range selected {
        node:=c.nodes[id]
        observed:=c.observed[id]
        if observed.Revision==req.Revision { result.AlreadyCurrent=append(result.AlreadyCurrent,id); continue }
        if !node.Online { result.Offline=append(result.Offline,id); result.BlockingReasons=append(result.BlockingReasons,"offline node: "+id); continue }
        if node.HeartbeatAt.IsZero() || now.Sub(node.HeartbeatAt)>2*time.Minute { result.StaleHeartbeat=append(result.StaleHeartbeat,id); result.BlockingReasons=append(result.BlockingReasons,"stale heartbeat: "+id); continue }
        pending=append(pending,id)
    }
    canarySet:=map[string]bool{}; for _,id:=range result.Canaries { canarySet[id]=true }
    canaryWave:=[]string{}; rest:=[]string{}
    for _,id:=range pending { if canarySet[id] { canaryWave=append(canaryWave,id) } else { rest=append(rest,id) } }
    if len(canaryWave)>0 { result.Waves=append(result.Waves,canaryWave) }
    for len(rest)>0 { n:=req.WaveSize; if n>len(rest) { n=len(rest) }; result.Waves=append(result.Waves,append([]string(nil),rest[:n]...)); rest=rest[n:] }
    sort.Strings(result.AlreadyCurrent); sort.Strings(result.Offline); sort.Strings(result.StaleHeartbeat); sort.Strings(result.BlockingReasons)
    if len(result.BlockingReasons)>0 { result.Risk="blocked" } else if len(result.Waves)>4 || len(selected)>50 { result.Risk="medium" }
    return result,nil
}
