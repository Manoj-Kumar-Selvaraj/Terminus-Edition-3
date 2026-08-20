package controlplane

import (
    "fmt"
    "sort"
    "strings"
    "time"
)

func (c *ControlPlane) Rollout(req RolloutRequest) (Rollout, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if req.Revision == 0 { req.Revision = c.desired.Revision }
    if req.Revision != c.desired.Revision { return Rollout{},fmt.Errorf("%w: rollout revision %d is not current %d",ErrConflict,req.Revision,c.desired.Revision) }
    if req.WaveSize < 1 { req.WaveSize = 5 }
    if req.WaveSize > c.cfg.MaxWave { return Rollout{},fmt.Errorf("wave_size %d exceeds maximum %d",req.WaveSize,c.cfg.MaxWave) }
    selected:=c.selectNodesLocked(req.Selector)
    if len(selected)==0 { return Rollout{},fmt.Errorf("no nodes match selector") }
    canaries:=uniqueSorted(req.CanaryNodes)
    selectedSet:=map[string]bool{}
    for _,id:=range selected { selectedSet[id]=true }
    for _,id:=range canaries { if !selectedSet[id] { return Rollout{},fmt.Errorf("canary %s is outside selector",id) } }
    ordered:=make([]string,0,len(selected))
    seen:=map[string]bool{}
    for _,id:=range canaries { if !seen[id] { seen[id]=true; ordered=append(ordered,id) } }
    for _,id:=range selected { if !seen[id] { seen[id]=true; ordered=append(ordered,id) } }
    waves:=make([]RolloutWave,0)
    offset:=0
    if len(canaries)>0 {
        nodes:=make([]RolloutNode,0,len(canaries))
        for _,id:=range canaries { nodes=append(nodes,RolloutNode{NodeID:id,Revision:req.Revision,Status:"pending"}) }
        waves=append(waves,RolloutWave{Index:0,Nodes:nodes,Status:"pending"})
        offset=len(canaries)
    }
    for offset<len(ordered) {
        end:=offset+req.WaveSize
        if end>len(ordered) { end=len(ordered) }
        nodes:=make([]RolloutNode,0,end-offset)
        for _,id:=range ordered[offset:end] { nodes=append(nodes,RolloutNode{NodeID:id,Revision:req.Revision,Status:"pending"}) }
        waves=append(waves,RolloutWave{Index:len(waves),Nodes:nodes,Status:"pending"})
        offset=end
    }
    rollout:=Rollout{ID:rolloutID(req),Revision:req.Revision,Selector:cloneLabels(req.Selector),Actor:req.Actor,Waves:waves,Status:"running",CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()}
    c.rollouts[rollout.ID]=cloneRollout(rollout)
    c.recordAuditLocked(req.Actor,"rollout.start","rollout",rollout.ID,req.Revision,map[string]any{"waves":len(waves),"nodes":len(selected)})
    if err:=c.persistLocked(); err!=nil { return Rollout{},err }
    for wi:=range rollout.Waves {
        wave:=rollout.Waves[wi]
        wave.Status="running"
        for ni:=range wave.Nodes {
            result:=wave.Nodes[ni]
            node:=c.nodes[result.NodeID]
            if !node.Online {
                result.Status="failed"
                result.Error="node offline"
                wave.Nodes[ni]=result
                wave.Status="failed"
                rollout.Status="failed"
                rollout.Waves[wi]=wave
                rollout.UpdatedAt=time.Now().UTC()
                c.rollouts[rollout.ID]=cloneRollout(rollout)
                c.recordAuditLocked(req.Actor,"rollout.node_failed","node",result.NodeID,req.Revision,map[string]any{"reason":"offline","wave":wi})
                _=c.persistLocked()
                return cloneRollout(rollout),nil
            }
            observed:=c.observed[result.NodeID]
            if observed.Revision==req.Revision {
                result.Status="already_current"
                wave.Nodes[ni]=result
                continue
            }
            before:=cloneObserved(observed)
            after:=desiredForNode(c.desired,result.NodeID)
            c.observed[result.NodeID]=after
            txn:=Transaction{ID:transactionID("rollout:"+rollout.ID+":"+result.NodeID,"rollout",req.Revision),PlanID:"rollout",IdempotencyKey:"rollout:"+rollout.ID+":"+result.NodeID,BaseRevision:before.Revision,TargetRevision:req.Revision,Actor:req.Actor,Phase:TransactionCommitted,Nodes:map[string]NodeTransaction{result.NodeID:{NodeID:result.NodeID,Before:before,After:after,Phase:TransactionCommitted}},CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()}
            c.transactions[txn.ID]=txn
            c.idempotency[txn.IdempotencyKey]=txn.ID
            result.Status="succeeded"
            wave.Nodes[ni]=result
            c.recordAuditLocked(req.Actor,"rollout.node_succeeded","node",result.NodeID,req.Revision,map[string]any{"wave":wi,"transaction_id":txn.ID})
        }
        if wave.Status!="failed" { wave.Status="succeeded" }
        rollout.Waves[wi]=wave
        rollout.UpdatedAt=time.Now().UTC()
        c.rollouts[rollout.ID]=cloneRollout(rollout)
        if err:=c.persistLocked(); err!=nil { return Rollout{},err }
    }
    rollout.Status="succeeded"
    rollout.UpdatedAt=time.Now().UTC()
    c.rollouts[rollout.ID]=cloneRollout(rollout)
    c.recordAuditLocked(req.Actor,"rollout.complete","rollout",rollout.ID,req.Revision,map[string]any{"status":rollout.Status})
    if err:=c.persistLocked(); err!=nil { return Rollout{},err }
    return cloneRollout(rollout),nil
}

func (c *ControlPlane) selectNodesLocked(selector map[string]string) []string {
    out:=[]string{}
    for id,node:=range c.nodes {
        matched:=true
        for key,value:=range selector {
            if node.Labels[key]!=value { matched=false; break }
        }
        if matched { out=append(out,id) }
    }
    sort.Strings(out)
    return out
}

func rolloutID(req RolloutRequest) string {
    parts:=[]string{fmt.Sprint(req.Revision),req.Actor,fmt.Sprint(req.WaveSize)}
    keys:=make([]string,0,len(req.Selector))
    for key:=range req.Selector { keys=append(keys,key) }
    sort.Strings(keys)
    for _,key:=range keys { parts=append(parts,key+"="+req.Selector[key]) }
    parts=append(parts,uniqueSorted(req.CanaryNodes)...)
    return transactionID(strings.Join(parts,"|"),"rollout",req.Revision)
}

func cloneRollout(in Rollout) Rollout {
    out:=in
    out.Selector=cloneLabels(in.Selector)
    out.Waves=make([]RolloutWave,len(in.Waves))
    for i,wave:=range in.Waves {
        out.Waves[i]=wave
        out.Waves[i].Nodes=append([]RolloutNode(nil),wave.Nodes...)
    }
    return out
}

func cloneLabels(in map[string]string) map[string]string {
    if in==nil { return nil }
    out:=map[string]string{}
    for key,value:=range in { out[key]=value }
    return out
}
