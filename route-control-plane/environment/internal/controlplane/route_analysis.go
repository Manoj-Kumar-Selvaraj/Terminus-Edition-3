package controlplane

import (
    "fmt"
    "net/netip"
    "sort"
)

type RouteShadow struct {
    NodeID string `json:"node_id"`
    Table int `json:"table"`
    Family string `json:"family"`
    ParentRoute string `json:"parent_route"`
    ChildRoute string `json:"child_route"`
    ParentPrefix string `json:"parent_prefix"`
    ChildPrefix string `json:"child_prefix"`
    Intentional bool `json:"intentional"`
    Reason string `json:"reason"`
}

type ECMPHealth struct {
    NodeID string `json:"node_id"`
    RouteID string `json:"route_id"`
    NextHops int `json:"next_hops"`
    Usable int `json:"usable"`
    TotalWeight int `json:"total_weight"`
    UsableWeight int `json:"usable_weight"`
    Healthy bool `json:"healthy"`
    Degraded bool `json:"degraded"`
}

type RouteAnalysisReport struct {
    Revision uint64 `json:"revision"`
    Shadows []RouteShadow `json:"shadows"`
    ECMP []ECMPHealth `json:"ecmp"`
    EmptyTables []string `json:"empty_tables"`
    OrphanTables []string `json:"orphan_tables"`
    DefaultRouteConflicts []string `json:"default_route_conflicts"`
    PrefixesByFamily map[string]int `json:"prefixes_by_family"`
}

func (c *ControlPlane) AnalyzeRoutes(nodeID string) RouteAnalysisReport {
    c.mu.RLock()
    defer c.mu.RUnlock()
    report:=RouteAnalysisReport{Revision:c.desired.Revision,PrefixesByFamily:map[string]int{}}
    groups:=map[string][]Route{}
    for _,raw:=range c.desired.Routes {
        if nodeID!="" && raw.NodeID!=nodeID { continue }
        route,err:=normalizeRoute(raw); if err!=nil { continue }
        key:=fmt.Sprintf("%s|%d|%s",route.NodeID,route.Table,route.Family)
        groups[key]=append(groups[key],route)
        report.PrefixesByFamily[route.Family]++
        if len(route.NextHops)>1 { report.ECMP=append(report.ECMP,ecmpHealth(c.desired.Links,route)) }
    }
    referencedTables:=map[string]bool{}
    for _,rule:=range c.desired.Rules {
        if nodeID!="" && rule.NodeID!=nodeID { continue }
        if rule.Action=="lookup" { referencedTables[fmt.Sprintf("%s|%d",rule.NodeID,rule.Table)]=true }
    }
    materializedTables:=map[string]bool{}
    for key,routes:=range groups {
        sort.Slice(routes,func(i,j int) bool {
            pi,_:=netip.ParsePrefix(routes[i].Destination); pj,_:=netip.ParsePrefix(routes[j].Destination)
            if pi.Bits()!=pj.Bits() { return pi.Bits()<pj.Bits() }
            if routes[i].Metric!=routes[j].Metric { return routes[i].Metric<routes[j].Metric }
            return routes[i].ID<routes[j].ID
        })
        defaults:=[]Route{}
        for i,parent:=range routes {
            p,_:=netip.ParsePrefix(parent.Destination)
            materializedTables[fmt.Sprintf("%s|%d",parent.NodeID,parent.Table)]=true
            if p.Bits()==0 { defaults=append(defaults,parent) }
            for j:=i+1;j<len(routes);j++ {
                child:=routes[j]; cp,_:=netip.ParsePrefix(child.Destination)
                if p.Addr().BitLen()!=cp.Addr().BitLen() || !p.Contains(cp.Addr()) || p.Bits()>=cp.Bits() { continue }
                intentional:=parent.Type=="blackhole" || child.Metric<=parent.Metric
                reason:="more-specific route overrides parent prefix"
                if parent.Type=="blackhole" { reason="more-specific route escapes a covering blackhole" }
                if child.Metric>parent.Metric { reason="more-specific route has a higher metric but still wins by prefix length" }
                report.Shadows=append(report.Shadows,RouteShadow{NodeID:parent.NodeID,Table:parent.Table,Family:parent.Family,ParentRoute:parent.ID,ChildRoute:child.ID,ParentPrefix:parent.Destination,ChildPrefix:child.Destination,Intentional:intentional,Reason:reason})
            }
        }
        if len(defaults)>1 {
            ids:=[]string{}; for _,r:=range defaults { ids=append(ids,fmt.Sprintf("%s(metric=%d)",r.ID,r.Metric)) }; sort.Strings(ids)
            report.DefaultRouteConflicts=append(report.DefaultRouteConflicts,key+":"+fmt.Sprint(ids))
        }
    }
    for table:=range referencedTables { if !materializedTables[table] { report.EmptyTables=append(report.EmptyTables,table) } }
    for table:=range materializedTables { if !referencedTables[table] { report.OrphanTables=append(report.OrphanTables,table) } }
    sort.Slice(report.Shadows,func(i,j int) bool { if report.Shadows[i].NodeID!=report.Shadows[j].NodeID { return report.Shadows[i].NodeID<report.Shadows[j].NodeID }; if report.Shadows[i].Table!=report.Shadows[j].Table { return report.Shadows[i].Table<report.Shadows[j].Table }; if report.Shadows[i].ParentPrefix!=report.Shadows[j].ParentPrefix { return report.Shadows[i].ParentPrefix<report.Shadows[j].ParentPrefix }; return report.Shadows[i].ChildPrefix<report.Shadows[j].ChildPrefix })
    sort.Slice(report.ECMP,func(i,j int) bool { if report.ECMP[i].NodeID!=report.ECMP[j].NodeID { return report.ECMP[i].NodeID<report.ECMP[j].NodeID }; return report.ECMP[i].RouteID<report.ECMP[j].RouteID })
    sort.Strings(report.EmptyTables); sort.Strings(report.OrphanTables); sort.Strings(report.DefaultRouteConflicts)
    return report
}

func ecmpHealth(links []Link,route Route) ECMPHealth {
    result:=ECMPHealth{NodeID:route.NodeID,RouteID:route.ID,NextHops:len(route.NextHops)}
    usable:=usableNextHops(links,route); result.Usable=len(usable)
    for _,hop:=range route.NextHops { weight:=hop.Weight; if weight<1 { weight=1 }; result.TotalWeight+=weight }
    for _,hop:=range usable { weight:=hop.Weight; if weight<1 { weight=1 }; result.UsableWeight+=weight }
    result.Healthy=result.Usable==result.NextHops && result.NextHops>0
    result.Degraded=result.Usable>0 && result.Usable<result.NextHops
    return result
}

func (c *ControlPlane) PrefixCoverage(nodeID string,table int) map[string][]string {
    c.mu.RLock(); defer c.mu.RUnlock()
    coverage:=map[string][]string{}
    for _,route:=range c.desired.Routes {
        if nodeID!="" && route.NodeID!=nodeID { continue }; if table>0 && route.Table!=table { continue }
        normalized,err:=normalizeRoute(route); if err!=nil { continue }
        key:=fmt.Sprintf("%s/table-%d/%s",normalized.NodeID,normalized.Table,normalized.Family)
        coverage[key]=append(coverage[key],normalized.Destination)
    }
    for key:=range coverage { sort.Slice(coverage[key],func(i,j int) bool { a,_:=netip.ParsePrefix(coverage[key][i]); b,_:=netip.ParsePrefix(coverage[key][j]); if a.Bits()!=b.Bits() { return a.Bits()<b.Bits() }; return coverage[key][i]<coverage[key][j] }) }
    return coverage
}
