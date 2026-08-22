package controlplane

import (
    "sort"
)

type InventorySummary struct {
    Revision uint64 `json:"revision"`
    Nodes int `json:"nodes"`
    OnlineNodes int `json:"online_nodes"`
    Routes int `json:"routes"`
    Rules int `json:"rules"`
    Links int `json:"links"`
    RouteTables int `json:"route_tables"`
    IPv4Routes int `json:"ipv4_routes"`
    IPv6Routes int `json:"ipv6_routes"`
    Owners map[string]int `json:"owners"`
    Sites map[string]int `json:"sites"`
    Environments map[string]int `json:"environments"`
    ObservedRevisions map[uint64]int `json:"observed_revisions"`
    DriftByKind map[string]int `json:"drift_by_kind"`
}

type NodeInventory struct {
    Node Node `json:"node"`
    DesiredRevision uint64 `json:"desired_revision"`
    ObservedRevision uint64 `json:"observed_revision"`
    Routes int `json:"routes"`
    Rules int `json:"rules"`
    Links int `json:"links"`
    Tables []int `json:"tables"`
    Drift int `json:"drift"`
}

func (c *ControlPlane) Inventory() InventorySummary {
    c.mu.RLock(); defer c.mu.RUnlock()
    out:=InventorySummary{Revision:c.desired.Revision,Nodes:len(c.nodes),Routes:len(c.desired.Routes),Rules:len(c.desired.Rules),Links:len(c.desired.Links),Owners:map[string]int{},Sites:map[string]int{},Environments:map[string]int{},ObservedRevisions:map[uint64]int{},DriftByKind:map[string]int{}}
    tables:=map[string]bool{}
    for _,node:=range c.nodes { if node.Online { out.OnlineNodes++ }; out.Sites[node.Site]++; out.Environments[node.Environment]++ }
    for _,route:=range c.desired.Routes {
        tables[route.NodeID+"|"+strconvI(route.Table)]=true
        if route.Family=="ipv6" { out.IPv6Routes++ } else { out.IPv4Routes++ }
        out.Owners[normalizeOwner(route.Owner)]++
    }
    out.RouteTables=len(tables)
    for _,state:=range c.observed { out.ObservedRevisions[state.Revision]++ }
    for _,item:=range c.driftLocked("") { out.DriftByKind[string(item.Kind)]++ }
    return out
}

func (c *ControlPlane) NodeInventory(nodeID string) (NodeInventory,error) {
    c.mu.RLock(); defer c.mu.RUnlock()
    node,ok:=c.nodes[nodeID]; if !ok { return NodeInventory{},ErrNotFound }
    out:=NodeInventory{Node:cloneNode(node),DesiredRevision:c.desired.Revision,ObservedRevision:c.observed[nodeID].Revision}
    tables:=map[int]bool{}
    for _,r:=range c.desired.Routes { if r.NodeID==nodeID { out.Routes++; tables[r.Table]=true } }
    for _,r:=range c.desired.Rules { if r.NodeID==nodeID { out.Rules++ } }
    for _,l:=range c.desired.Links { if l.NodeID==nodeID { out.Links++ } }
    for table:=range tables { out.Tables=append(out.Tables,table) }; sort.Ints(out.Tables)
    out.Drift=len(c.driftLocked(nodeID))
    return out,nil
}
