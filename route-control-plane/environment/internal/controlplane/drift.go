package controlplane

import (
    "fmt"
    "reflect"
    "sort"
    "strings"
    "time"
)

func (c *ControlPlane) Drift(nodeID string) []DriftItem {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.driftLocked(nodeID)
}

func (c *ControlPlane) driftLocked(nodeID string) []DriftItem {
    nodes := []string{}
    if nodeID != "" {
        nodes = append(nodes, nodeID)
    } else {
        for id := range c.nodes { nodes = append(nodes, id) }
        sort.Strings(nodes)
    }
    var out []DriftItem
    for _, id := range nodes {
        observed, ok := c.observed[id]
        if !ok { observed = ObservedState{} }
        desiredRoutes := map[string]Route{}
        observedRoutes := map[string]Route{}
        for _, route := range c.desired.Routes {
            if route.NodeID == id { desiredRoutes[routeIdentity(route)] = route }
        }
        for _, route := range observed.Routes {
            if route.NodeID == id { observedRoutes[routeIdentity(route)] = route }
        }
        for identity, desired := range desiredRoutes {
            current, exists := observedRoutes[identity]
            if !exists {
                out = append(out, DriftItem{NodeID:id,Kind:DriftMissing,ObjectType:"route",ObjectID:desired.ID,Desired:desired,Owned:desired.Owner=="routecp"})
                continue
            }
            if !routeEquivalent(desired, current) {
                out = append(out, DriftItem{NodeID:id,Kind:DriftChanged,ObjectType:"route",ObjectID:desired.ID,Desired:desired,Observed:current,Owned:desired.Owner=="routecp"})
            }
        }
        for identity, current := range observedRoutes {
            if _, exists := desiredRoutes[identity]; exists { continue }
            out = append(out, DriftItem{NodeID:id,Kind:DriftUnexpected,ObjectType:"route",ObjectID:current.ID,Observed:current,Owned:current.Owner=="routecp"})
        }

        desiredRules := map[string]PolicyRule{}
        observedRules := map[string]PolicyRule{}
        for _, rule := range c.desired.Rules {
            if rule.NodeID == id { desiredRules[ruleIdentity(rule)] = rule }
        }
        for _, rule := range observed.Rules {
            if rule.NodeID == id { observedRules[ruleIdentity(rule)] = rule }
        }
        for identity, desired := range desiredRules {
            current, exists := observedRules[identity]
            if !exists {
                out = append(out, DriftItem{NodeID:id,Kind:DriftMissing,ObjectType:"rule",ObjectID:desired.ID,Desired:desired,Owned:desired.Owner=="routecp"})
                continue
            }
            if !ruleEquivalent(desired, current) {
                out = append(out, DriftItem{NodeID:id,Kind:DriftChanged,ObjectType:"rule",ObjectID:desired.ID,Desired:desired,Observed:current,Owned:desired.Owner=="routecp"})
            }
        }
        for identity, current := range observedRules {
            if _, exists := desiredRules[identity]; exists { continue }
            out = append(out, DriftItem{NodeID:id,Kind:DriftUnexpected,ObjectType:"rule",ObjectID:current.ID,Observed:current,Owned:current.Owner=="routecp"})
        }
    }
    sort.Slice(out, func(i,j int) bool {
        if out[i].NodeID != out[j].NodeID { return out[i].NodeID < out[j].NodeID }
        if out[i].ObjectType != out[j].ObjectType { return out[i].ObjectType < out[j].ObjectType }
        if out[i].ObjectID != out[j].ObjectID { return out[i].ObjectID < out[j].ObjectID }
        return out[i].Kind < out[j].Kind
    })
    return out
}

func (c *ControlPlane) Reconcile(req ReconcileRequest) (ReconcileResult, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if req.NodeID == "" { return ReconcileResult{}, fmt.Errorf("node_id is required") }
    node, ok := c.nodes[req.NodeID]
    if !ok { return ReconcileResult{}, fmt.Errorf("%w: node %s", ErrNotFound, req.NodeID) }
    if !node.Online { return ReconcileResult{}, fmt.Errorf("node %s is offline", req.NodeID) }
    observed := c.observed[req.NodeID]
    if req.ExpectedObservedRevision != 0 && observed.Revision != req.ExpectedObservedRevision {
        return ReconcileResult{}, fmt.Errorf("%w: observed revision %d does not match expected %d", ErrConflict, observed.Revision, req.ExpectedObservedRevision)
    }
    drift := c.driftLocked(req.NodeID)
    actionable := make([]DriftItem,0,len(drift))
    for _, item := range drift {
        if item.Kind == DriftUnexpected && !item.Owned { continue }
        actionable = append(actionable,item)
    }
    result := ReconcileResult{NodeID:req.NodeID,Drift:actionable,Applied:false}
    if req.DryRun || len(actionable)==0 { return result,nil }
    before := cloneObserved(observed)
    after := desiredForNode(c.desired, req.NodeID)
    txn := Transaction{
        ID: transactionID("reconcile:"+req.NodeID+":"+fmt.Sprint(time.Now().UnixNano()), "reconcile", c.desired.Revision),
        PlanID:"reconcile",
        IdempotencyKey:"reconcile:"+req.NodeID+":"+fmt.Sprint(observed.Revision),
        BaseRevision:observed.Revision,
        TargetRevision:c.desired.Revision,
        Actor:req.Actor,
        Phase:TransactionCommitted,
        Nodes:map[string]NodeTransaction{req.NodeID:{NodeID:req.NodeID,Before:before,After:after,Phase:TransactionCommitted}},
        CreatedAt:time.Now().UTC(),
        UpdatedAt:time.Now().UTC(),
    }
    c.observed[req.NodeID]=after
    c.transactions[txn.ID]=txn
    c.idempotency[txn.IdempotencyKey]=txn.ID
    c.recordAuditLocked(req.Actor,"reconcile.commit","node",req.NodeID,c.desired.Revision,map[string]any{"drift_items":len(actionable)})
    if err:=c.persistLocked(); err!=nil { return ReconcileResult{},err }
    result.Applied=true
    result.TransactionID=txn.ID
    return result,nil
}

func routeEquivalent(a,b Route) bool {
    an,errA:=normalizeRoute(a)
    bn,errB:=normalizeRoute(b)
    if errA!=nil || errB!=nil { return false }
    ah:=stableNextHops(an.NextHops)
    bh:=stableNextHops(bn.NextHops)
    if len(ah)!=len(bh) { return false }
    an.NextHops=nil
    bn.NextHops=nil
    if !reflect.DeepEqual(an,bn) { return false }
    for i:=range ah { if ah[i]!=bh[i] { return false } }
    return true
}

func ruleEquivalent(a,b PolicyRule) bool {
    an,errA:=normalizeRule(a)
    bn,errB:=normalizeRule(b)
    if errA!=nil || errB!=nil { return false }
    return an==bn
}

func normalizeOwner(value string) string { return strings.ToLower(strings.TrimSpace(value)) }
