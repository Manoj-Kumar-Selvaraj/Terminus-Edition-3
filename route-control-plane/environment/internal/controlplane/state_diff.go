package controlplane

import (
    "fmt"
    "sort"
)

type ObjectDelta struct {
    NodeID string `json:"node_id"`
    ObjectType string `json:"object_type"`
    ObjectID string `json:"object_id"`
    Change string `json:"change"`
    Owned bool `json:"owned"`
    Desired any `json:"desired,omitempty"`
    Observed any `json:"observed,omitempty"`
}

type NodeStateDiff struct {
    NodeID string `json:"node_id"`
    DesiredRevision uint64 `json:"desired_revision"`
    ObservedRevision uint64 `json:"observed_revision"`
    Deltas []ObjectDelta `json:"deltas"`
    OwnedChanges int `json:"owned_changes"`
    UnownedChanges int `json:"unowned_changes"`
    InSync bool `json:"in_sync"`
}

type StateDiffReport struct {
    DesiredRevision uint64 `json:"desired_revision"`
    Nodes []NodeStateDiff `json:"nodes"`
    TotalDeltas int `json:"total_deltas"`
    NodesInSync int `json:"nodes_in_sync"`
    NodesOutOfSync int `json:"nodes_out_of_sync"`
}

func (c *ControlPlane) StateDiff(nodeID string) StateDiffReport {
    c.mu.RLock(); defer c.mu.RUnlock()
    report:=StateDiffReport{DesiredRevision:c.desired.Revision}
    ids:=make([]string,0,len(c.nodes)); for id:=range c.nodes { if nodeID=="" || id==nodeID { ids=append(ids,id) } }; sort.Strings(ids)
    for _,id:=range ids {
        observed:=c.observed[id]; node:=NodeStateDiff{NodeID:id,DesiredRevision:c.desired.Revision,ObservedRevision:observed.Revision}
        node.Deltas=append(node.Deltas,diffRoutes(id,c.desired.Routes,observed.Routes)...)
        node.Deltas=append(node.Deltas,diffRules(id,c.desired.Rules,observed.Rules)...)
        node.Deltas=append(node.Deltas,diffLinks(id,c.desired.Links,observed.Links)...)
        sort.Slice(node.Deltas,func(i,j int) bool { if node.Deltas[i].ObjectType!=node.Deltas[j].ObjectType { return node.Deltas[i].ObjectType<node.Deltas[j].ObjectType }; if node.Deltas[i].ObjectID!=node.Deltas[j].ObjectID { return node.Deltas[i].ObjectID<node.Deltas[j].ObjectID }; return node.Deltas[i].Change<node.Deltas[j].Change })
        for _,d:=range node.Deltas { if d.Owned { node.OwnedChanges++ } else { node.UnownedChanges++ } }
        node.InSync=len(node.Deltas)==0 && observed.Revision==c.desired.Revision
        if node.InSync { report.NodesInSync++ } else { report.NodesOutOfSync++ }
        report.TotalDeltas+=len(node.Deltas); report.Nodes=append(report.Nodes,node)
    }
    return report
}

func diffRoutes(nodeID string,desired,observed []Route) []ObjectDelta {
    want:=map[string]Route{}; got:=map[string]Route{}
    for _,r:=range desired { if r.NodeID==nodeID { normalized,err:=normalizeRoute(r); if err==nil { want[routeIdentity(normalized)]=normalized } } }
    for _,r:=range observed { if r.NodeID==nodeID { normalized,err:=normalizeRoute(r); if err==nil { got[routeIdentity(normalized)]=normalized } } }
    out:=[]ObjectDelta{}
    for key,w:=range want { g,ok:=got[key]; if !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"route",ObjectID:w.ID,Change:"missing",Owned:normalizeOwner(w.Owner)=="routecp",Desired:w}); continue }; if !routeEquivalent(w,g) { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"route",ObjectID:w.ID,Change:"changed",Owned:normalizeOwner(w.Owner)=="routecp",Desired:w,Observed:g}) } }
    for key,g:=range got { if _,ok:=want[key]; !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"route",ObjectID:g.ID,Change:"unexpected",Owned:normalizeOwner(g.Owner)=="routecp",Observed:g}) } }
    return out
}

func diffRules(nodeID string,desired,observed []PolicyRule) []ObjectDelta {
    want:=map[string]PolicyRule{}; got:=map[string]PolicyRule{}
    for _,r:=range desired { if r.NodeID==nodeID { normalized,err:=normalizeRule(r); if err==nil { want[ruleIdentity(normalized)]=normalized } } }
    for _,r:=range observed { if r.NodeID==nodeID { normalized,err:=normalizeRule(r); if err==nil { got[ruleIdentity(normalized)]=normalized } } }
    out:=[]ObjectDelta{}
    for key,w:=range want { g,ok:=got[key]; if !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"rule",ObjectID:w.ID,Change:"missing",Owned:normalizeOwner(w.Owner)=="routecp",Desired:w}); continue }; if !ruleEquivalent(w,g) { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"rule",ObjectID:w.ID,Change:"changed",Owned:normalizeOwner(w.Owner)=="routecp",Desired:w,Observed:g}) } }
    for key,g:=range got { if _,ok:=want[key]; !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"rule",ObjectID:g.ID,Change:"unexpected",Owned:normalizeOwner(g.Owner)=="routecp",Observed:g}) } }
    return out
}

func diffLinks(nodeID string,desired,observed []Link) []ObjectDelta {
    want:=map[string]Link{}; got:=map[string]Link{}
    for _,l:=range desired { if l.NodeID==nodeID { want[l.Name]=cloneLink(l) } }; for _,l:=range observed { if l.NodeID==nodeID { got[l.Name]=cloneLink(l) } }
    out:=[]ObjectDelta{}
    for name,w:=range want { g,ok:=got[name]; if !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"link",ObjectID:name,Change:"missing",Owned:true,Desired:w}); continue }; if fmt.Sprint(w)!=fmt.Sprint(g) { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"link",ObjectID:name,Change:"changed",Owned:true,Desired:w,Observed:g}) } }
    for name,g:=range got { if _,ok:=want[name]; !ok { out=append(out,ObjectDelta{NodeID:nodeID,ObjectType:"link",ObjectID:name,Change:"unexpected",Owned:false,Observed:g}) } }
    return out
}
