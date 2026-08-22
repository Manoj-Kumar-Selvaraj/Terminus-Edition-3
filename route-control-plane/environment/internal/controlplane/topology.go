package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
)

type LinkHealth struct {
    NodeID string `json:"node_id"`
    Name string `json:"name"`
    Up bool `json:"up"`
    AddressCount int `json:"address_count"`
    ReferencedRoutes int `json:"referenced_routes"`
    GatewayCount int `json:"gateway_count"`
    Orphaned bool `json:"orphaned"`
}

type NodeTopology struct {
    NodeID string `json:"node_id"`
    Site string `json:"site"`
    Environment string `json:"environment"`
    ManagementIP string `json:"management_ip"`
    Online bool `json:"online"`
    Links []LinkHealth `json:"links"`
    RouteTables []int `json:"route_tables"`
    RuleCount int `json:"rule_count"`
    UnreachableGateways []string `json:"unreachable_gateways"`
}

type TopologyReport struct {
    Revision uint64 `json:"revision"`
    Nodes []NodeTopology `json:"nodes"`
    Sites map[string]int `json:"sites"`
    Environments map[string]int `json:"environments"`
}

type DependencyEdge struct {
    From string `json:"from"`
    To string `json:"to"`
    Kind string `json:"kind"`
    Critical bool `json:"critical"`
}

type DependencyGraph struct {
    NodeID string `json:"node_id"`
    Vertices []string `json:"vertices"`
    Edges []DependencyEdge `json:"edges"`
    Cycles [][]string `json:"cycles"`
}

func (c *ControlPlane) Topology(nodeID string) TopologyReport {
    c.mu.RLock()
    defer c.mu.RUnlock()
    report := TopologyReport{Revision:c.desired.Revision,Sites:map[string]int{},Environments:map[string]int{}}
    ids := make([]string,0,len(c.nodes))
    for id := range c.nodes { if nodeID == "" || id == nodeID { ids = append(ids,id) } }
    sort.Strings(ids)
    for _, id := range ids {
        node := c.nodes[id]
        report.Sites[node.Site]++
        report.Environments[node.Environment]++
        topo := NodeTopology{NodeID:id,Site:node.Site,Environment:node.Environment,ManagementIP:node.ManagementIP,Online:node.Online}
        tableSet := map[int]bool{}
        linkRoutes := map[string]int{}
        linkGateways := map[string]int{}
        for _, route := range c.desired.Routes {
            if route.NodeID != id { continue }
            tableSet[route.Table] = true
            for _, hop := range route.NextHops {
                if hop.Interface != "" { linkRoutes[hop.Interface]++ }
                if hop.Gateway != "" { linkGateways[hop.Interface]++ }
                if hop.Gateway != "" && !gatewayOnLink(c.desired.Links, id, hop.Interface, hop.Gateway) {
                    topo.UnreachableGateways = append(topo.UnreachableGateways, fmt.Sprintf("%s via %s",hop.Gateway,hop.Interface))
                }
            }
        }
        for table := range tableSet { topo.RouteTables = append(topo.RouteTables,table) }
        sort.Ints(topo.RouteTables)
        for _, rule := range c.desired.Rules { if rule.NodeID == id { topo.RuleCount++ } }
        links := make([]Link,0)
        for _, link := range c.desired.Links { if link.NodeID == id { links = append(links,link) } }
        sort.Slice(links,func(i,j int) bool { return links[i].Name < links[j].Name })
        for _, link := range links {
            topo.Links = append(topo.Links,LinkHealth{NodeID:id,Name:link.Name,Up:link.Up,AddressCount:len(link.Addresses),ReferencedRoutes:linkRoutes[link.Name],GatewayCount:linkGateways[link.Name],Orphaned:linkRoutes[link.Name]==0})
        }
        sort.Strings(topo.UnreachableGateways)
        report.Nodes = append(report.Nodes,topo)
    }
    return report
}

func gatewayOnLink(links []Link, nodeID, interfaceName, gateway string) bool {
    if gateway == "" { return true }
    addr, err := netip.ParseAddr(gateway)
    if err != nil { return false }
    for _, link := range links {
        if link.NodeID != nodeID || link.Name != interfaceName || !link.Up { continue }
        for _, raw := range link.Addresses {
            p, parseErr := netip.ParsePrefix(raw)
            if parseErr == nil && p.Contains(addr) { return true }
        }
    }
    return false
}

func (c *ControlPlane) Dependencies(nodeID string) DependencyGraph {
    c.mu.RLock()
    defer c.mu.RUnlock()
    graph := DependencyGraph{NodeID:nodeID}
    vertices := map[string]bool{}
    addVertex := func(v string) { if v != "" { vertices[v]=true } }
    for _, link := range c.desired.Links {
        if nodeID != "" && link.NodeID != nodeID { continue }
        addVertex("node:"+link.NodeID)
        addVertex("link:"+link.NodeID+":"+link.Name)
        graph.Edges = append(graph.Edges,DependencyEdge{From:"node:"+link.NodeID,To:"link:"+link.NodeID+":"+link.Name,Kind:"owns_link"})
    }
    for _, route := range c.desired.Routes {
        if nodeID != "" && route.NodeID != nodeID { continue }
        routeV := "route:"+route.NodeID+":"+route.ID
        tableV := fmt.Sprintf("table:%s:%d",route.NodeID,route.Table)
        addVertex(routeV); addVertex(tableV); addVertex("node:"+route.NodeID)
        graph.Edges = append(graph.Edges,DependencyEdge{From:"node:"+route.NodeID,To:routeV,Kind:"owns_route"})
        graph.Edges = append(graph.Edges,DependencyEdge{From:routeV,To:tableV,Kind:"member_of_table"})
        for _, hop := range route.NextHops {
            if hop.Interface == "" { continue }
            linkV := "link:"+route.NodeID+":"+hop.Interface
            addVertex(linkV)
            graph.Edges = append(graph.Edges,DependencyEdge{From:routeV,To:linkV,Kind:"uses_link",Critical:true})
        }
    }
    for _, rule := range c.desired.Rules {
        if nodeID != "" && rule.NodeID != nodeID { continue }
        ruleV := "rule:"+rule.NodeID+":"+rule.ID
        tableV := fmt.Sprintf("table:%s:%d",rule.NodeID,rule.Table)
        addVertex(ruleV); addVertex(tableV); addVertex("node:"+rule.NodeID)
        graph.Edges = append(graph.Edges,DependencyEdge{From:"node:"+rule.NodeID,To:ruleV,Kind:"owns_rule"})
        if rule.Action == "lookup" { graph.Edges = append(graph.Edges,DependencyEdge{From:ruleV,To:tableV,Kind:"lookup",Critical:true}) }
    }
    for v := range vertices { graph.Vertices = append(graph.Vertices,v) }
    sort.Strings(graph.Vertices)
    sort.Slice(graph.Edges,func(i,j int) bool {
        if graph.Edges[i].From != graph.Edges[j].From { return graph.Edges[i].From < graph.Edges[j].From }
        if graph.Edges[i].To != graph.Edges[j].To { return graph.Edges[i].To < graph.Edges[j].To }
        return graph.Edges[i].Kind < graph.Edges[j].Kind
    })
    graph.Cycles = dependencyCycles(graph.Vertices,graph.Edges)
    return graph
}

func dependencyCycles(vertices []string, edges []DependencyEdge) [][]string {
    adjacency := map[string][]string{}
    for _, edge := range edges { adjacency[edge.From] = append(adjacency[edge.From],edge.To) }
    color := map[string]int{}
    stack := []string{}
    index := map[string]int{}
    cycles := [][]string{}
    var visit func(string)
    visit = func(v string) {
        color[v]=1; index[v]=len(stack); stack=append(stack,v)
        for _, next := range adjacency[v] {
            if color[next]==0 { visit(next); continue }
            if color[next]==1 {
                start:=index[next]
                cycle:=append([]string(nil),stack[start:]...)
                cycle=append(cycle,next)
                cycles=append(cycles,cycle)
            }
        }
        stack=stack[:len(stack)-1]; delete(index,v); color[v]=2
    }
    for _, v := range vertices { if color[v]==0 { visit(v) } }
    return cycles
}
