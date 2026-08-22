package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
    "strings"
)

type TraceRequest struct {
    NodeID string `json:"node_id"`
    Source string `json:"source"`
    Destination string `json:"destination"`
    Mark int `json:"mark"`
    InputInterface string `json:"input_interface"`
    OutputInterface string `json:"output_interface"`
}

type TraceDecision struct {
    NodeID string `json:"node_id"`
    Family string `json:"family"`
    Table int `json:"table"`
    MatchedRule *PolicyRule `json:"matched_rule,omitempty"`
    Route *Route `json:"route,omitempty"`
    NextHops []NextHop `json:"next_hops,omitempty"`
    Reachable bool `json:"reachable"`
    Reasons []string `json:"reasons"`
}

type RouteTableSummary struct {
    NodeID string `json:"node_id"`
    Table int `json:"table"`
    Family string `json:"family"`
    RouteCount int `json:"route_count"`
    DefaultRoutes int `json:"default_routes"`
    Blackholes int `json:"blackholes"`
    Owners map[string]int `json:"owners"`
}

func (c *ControlPlane) Trace(req TraceRequest) (TraceDecision, error) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return traceState(c.desired, c.nodes, req)
}

func traceState(state DesiredState, nodes map[string]Node, req TraceRequest) (TraceDecision, error) {
    nodeID := strings.TrimSpace(req.NodeID)
    node, ok := nodes[nodeID]
    if !ok {
        return TraceDecision{}, fmt.Errorf("%w: node %s", ErrNotFound, nodeID)
    }
    destination, err := canonicalAddress(req.Destination)
    if err != nil || destination == "" {
        if err == nil { err = fmt.Errorf("destination is required") }
        return TraceDecision{}, err
    }
    family := "ipv4"
    if addr, parseErr := netip.ParseAddr(destination); parseErr == nil && addr.Is6() { family = "ipv6" }
    decision := TraceDecision{NodeID:nodeID, Family:family, Reasons:[]string{}}
    if !node.Online {
        decision.Reasons = append(decision.Reasons, "node is administratively offline")
    }

    rules := make([]PolicyRule, 0)
    for _, raw := range state.Rules {
        if raw.NodeID != nodeID { continue }
        rule, normErr := normalizeRule(raw)
        if normErr != nil { continue }
        if rule.Family != "" && rule.Family != family { continue }
        rules = append(rules, rule)
    }
    sort.SliceStable(rules, func(i, j int) bool {
        if rules[i].Priority != rules[j].Priority { return rules[i].Priority < rules[j].Priority }
        return rules[i].ID < rules[j].ID
    })

    table := 254
    for i := range rules {
        if ruleMatches(rules[i], req, destination) {
            r := rules[i]
            decision.MatchedRule = &r
            if r.Action == "blackhole" || r.Action == "unreachable" || r.Action == "prohibit" {
                decision.Reasons = append(decision.Reasons, "policy rule terminates lookup with "+r.Action)
                return decision, nil
            }
            if r.Action == "lookup" && r.Table > 0 {
                table = r.Table
                break
            }
        }
    }
    decision.Table = table

    route, found := bestRoute(state.Routes, nodeID, family, table, destination)
    if !found && table != 254 {
        decision.Reasons = append(decision.Reasons, fmt.Sprintf("no route in policy table %d", table))
        return decision, nil
    }
    if !found {
        route, found = bestRouteAnyTable(state.Routes, nodeID, family, destination)
    }
    if !found {
        decision.Reasons = append(decision.Reasons, "no matching route")
        return decision, nil
    }
    decision.Route = &route
    decision.Table = route.Table
    if route.Type == "blackhole" || route.Type == "unreachable" || route.Type == "prohibit" {
        decision.Reasons = append(decision.Reasons, "route terminates forwarding with "+route.Type)
        return decision, nil
    }
    usable := usableNextHops(state.Links, route)
    decision.NextHops = usable
    if len(route.NextHops) == 0 {
        decision.Reachable = route.Type == "local" || route.Type == "broadcast"
    } else {
        decision.Reachable = len(usable) > 0
    }
    if !decision.Reachable {
        decision.Reasons = append(decision.Reasons, "all candidate next hops are unavailable")
    }
    return decision, nil
}

func ruleMatches(rule PolicyRule, req TraceRequest, destination string) bool {
    if rule.Mark != 0 && req.Mark != rule.Mark { return false }
    if rule.InputInterface != "" && strings.TrimSpace(req.InputInterface) != rule.InputInterface { return false }
    if rule.OutputInterface != "" && strings.TrimSpace(req.OutputInterface) != rule.OutputInterface { return false }
    if rule.Source != "" {
        src, err := canonicalAddress(req.Source)
        if err != nil || src == "" || !prefixContains(rule.Source, src) { return false }
    }
    if rule.Destination != "" && !prefixContains(rule.Destination, destination) { return false }
    return true
}

func bestRoute(routes []Route, nodeID, family string, table int, destination string) (Route, bool) {
    var best Route
    bestBits := -1
    found := false
    for _, raw := range routes {
        if raw.NodeID != nodeID || raw.Table != table { continue }
        route, err := normalizeRoute(raw)
        if err != nil || route.Family != family { continue }
        p, err := netip.ParsePrefix(route.Destination)
        if err != nil { continue }
        a, err := netip.ParseAddr(destination)
        if err != nil || !p.Contains(a) { continue }
        bits := p.Bits()
        if !found || bits > bestBits || (bits == bestBits && route.Metric < best.Metric) || (bits == bestBits && route.Metric == best.Metric && route.ID < best.ID) {
            best = route
            bestBits = bits
            found = true
        }
    }
    return best, found
}

func bestRouteAnyTable(routes []Route, nodeID, family, destination string) (Route, bool) {
    tables := map[int]bool{}
    for _, route := range routes {
        if route.NodeID == nodeID { tables[route.Table] = true }
    }
    ordered := make([]int, 0, len(tables))
    for table := range tables { ordered = append(ordered, table) }
    sort.Ints(ordered)
    for _, table := range ordered {
        if route, ok := bestRoute(routes, nodeID, family, table, destination); ok { return route, true }
    }
    return Route{}, false
}

func usableNextHops(links []Link, route Route) []NextHop {
    up := map[string]bool{}
    for _, link := range links {
        if link.NodeID == route.NodeID { up[link.Name] = link.Up }
    }
    out := make([]NextHop, 0, len(route.NextHops))
    for _, hop := range stableNextHops(route.NextHops) {
        if hop.Interface == "" || up[hop.Interface] { out = append(out, hop) }
    }
    return out
}

func (c *ControlPlane) RouteTables(nodeID string) []RouteTableSummary {
    c.mu.RLock()
    defer c.mu.RUnlock()
    index := map[string]*RouteTableSummary{}
    for _, raw := range c.desired.Routes {
        if nodeID != "" && raw.NodeID != nodeID { continue }
        route, err := normalizeRoute(raw)
        if err != nil { continue }
        key := fmt.Sprintf("%s|%d|%s", route.NodeID, route.Table, route.Family)
        summary := index[key]
        if summary == nil {
            summary = &RouteTableSummary{NodeID:route.NodeID,Table:route.Table,Family:route.Family,Owners:map[string]int{}}
            index[key] = summary
        }
        summary.RouteCount++
        if route.Destination == "0.0.0.0/0" || route.Destination == "::/0" { summary.DefaultRoutes++ }
        if route.Type == "blackhole" { summary.Blackholes++ }
        summary.Owners[normalizeOwner(route.Owner)]++
    }
    out := make([]RouteTableSummary, 0, len(index))
    for _, summary := range index { out = append(out, *summary) }
    sort.Slice(out, func(i,j int) bool {
        if out[i].NodeID != out[j].NodeID { return out[i].NodeID < out[j].NodeID }
        if out[i].Table != out[j].Table { return out[i].Table < out[j].Table }
        return out[i].Family < out[j].Family
    })
    return out
}
