package controlplane

import (
    "fmt"
    "sort"
    "time"
)

type ChangeWindowRequest struct {
    Selector map[string]string `json:"selector"`
    WaveSize int `json:"wave_size"`
    MaxFailureDomainsPerWave int `json:"max_failure_domains_per_wave"`
    RequireFreshHeartbeat bool `json:"require_fresh_heartbeat"`
}

type ChangeWindowWave struct {
    Index int `json:"index"`
    Nodes []string `json:"nodes"`
    Sites []string `json:"sites"`
    Environments []string `json:"environments"`
    AlreadyCurrent []string `json:"already_current"`
    Risk string `json:"risk"`
}

type ChangeWindowPlan struct {
    Revision uint64 `json:"revision"`
    Waves []ChangeWindowWave `json:"waves"`
    Excluded map[string]string `json:"excluded"`
    Selected int `json:"selected"`
    Planned int `json:"planned"`
    Risk string `json:"risk"`
    Reasons []string `json:"reasons"`
}

func (c *ControlPlane) PlanChangeWindow(req ChangeWindowRequest) (ChangeWindowPlan,error) {
    c.mu.RLock(); defer c.mu.RUnlock()
    if req.WaveSize<1 { req.WaveSize=5 }; if req.WaveSize>c.cfg.MaxWave { return ChangeWindowPlan{},fmt.Errorf("wave_size %d exceeds maximum %d",req.WaveSize,c.cfg.MaxWave) }
    if req.MaxFailureDomainsPerWave<1 { req.MaxFailureDomainsPerWave=1 }
    selected:=c.selectNodesLocked(req.Selector); if len(selected)==0 { return ChangeWindowPlan{},fmt.Errorf("no nodes match selector") }
    plan:=ChangeWindowPlan{Revision:c.desired.Revision,Selected:len(selected),Excluded:map[string]string{},Risk:"low"}
    now:=time.Now().UTC(); eligible:=[]string{}
    for _,id:=range selected {
        node:=c.nodes[id]
        if !node.Online { plan.Excluded[id]="offline"; continue }
        if req.RequireFreshHeartbeat && (node.HeartbeatAt.IsZero() || now.Sub(node.HeartbeatAt)>2*time.Minute) { plan.Excluded[id]="stale heartbeat"; continue }
        if observed:=c.observed[id]; observed.Revision==c.desired.Revision { plan.Excluded[id]="already current"; continue }
        eligible=append(eligible,id)
    }
    bySite:=map[string][]string{}; siteKeys:=[]string{}
    for _,id:=range eligible { site:=c.nodes[id].Site; if _,ok:=bySite[site]; !ok { siteKeys=append(siteKeys,site) }; bySite[site]=append(bySite[site],id) }
    sort.Strings(siteKeys); for _,site:=range siteKeys { sort.Strings(bySite[site]) }
    remaining:=len(eligible); waveIndex:=0
    cursors:=map[string]int{}
    for remaining>0 {
        wave:=ChangeWindowWave{Index:waveIndex,Risk:"low"}; domains:=0
        for _,site:=range siteKeys {
            if domains>=req.MaxFailureDomainsPerWave || len(wave.Nodes)>=req.WaveSize { break }
            cursor:=cursors[site]; if cursor>=len(bySite[site]) { continue }
            domains++; wave.Sites=append(wave.Sites,site)
            for cursor<len(bySite[site]) && len(wave.Nodes)<req.WaveSize {
                id:=bySite[site][cursor]; wave.Nodes=append(wave.Nodes,id); env:=c.nodes[id].Environment; if !containsString(wave.Environments,env) { wave.Environments=append(wave.Environments,env) }; cursor++; remaining--
            }
            cursors[site]=cursor
        }
        if len(wave.Nodes)==0 { break }
        sort.Strings(wave.Sites); sort.Strings(wave.Environments)
        if len(wave.Sites)>1 { wave.Risk="medium" }; if len(wave.Environments)>1 { wave.Risk="high" }
        plan.Waves=append(plan.Waves,wave); plan.Planned+=len(wave.Nodes); waveIndex++
    }
    if len(plan.Excluded)>0 { plan.Risk="medium"; plan.Reasons=append(plan.Reasons,"some selected nodes are excluded from the window") }
    for _,wave:=range plan.Waves { if wave.Risk=="high" { plan.Risk="high"; plan.Reasons=append(plan.Reasons,"a wave crosses environment boundaries") } }
    if plan.Planned==0 { plan.Risk="blocked"; plan.Reasons=append(plan.Reasons,"no eligible nodes remain after safety filters") }
    sort.Strings(plan.Reasons)
    return plan,nil
}

func containsString(values []string,value string) bool { for _,v:=range values { if v==value { return true } }; return false }
