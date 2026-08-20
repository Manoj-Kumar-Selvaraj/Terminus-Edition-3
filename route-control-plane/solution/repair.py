#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/app/routecp")


def replace_go_function(text: str, signature: str, replacement: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"function signature not found: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError(f"opening brace not found: {signature}")
    depth = 0
    in_string = False
    in_raw = False
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if in_raw:
            if ch == "`":
                in_raw = False
        elif in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "`":
                in_raw = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return text[:start] + replacement.rstrip() + "\n" + text[end:]
        i += 1
    raise RuntimeError(f"unterminated function: {signature}")


def patch_go(path: pathlib.Path, replacements: list[tuple[str, str]]) -> None:
    text = path.read_text()
    for signature, replacement in replacements:
        text = replace_go_function(text, signature, replacement)
    path.write_text(text)


domain = ROOT / "internal/controlplane/domain.go"
patch_go(domain, [
    ("func canonicalPrefix(value string)", r'''func canonicalPrefix(value string) (string, error) {
    value = strings.TrimSpace(value)
    if value == "" {
        return "", fmt.Errorf("prefix is required")
    }
    if value == "default" {
        return "0.0.0.0/0", nil
    }
    prefix, err := netip.ParsePrefix(value)
    if err != nil {
        return "", fmt.Errorf("parse prefix %q: %w", value, err)
    }
    return prefix.Masked().String(), nil
}'''),
    ("func normalizeRoute(route Route)", r'''func normalizeRoute(route Route) (Route, error) {
    route.ID = strings.TrimSpace(route.ID)
    route.NodeID = strings.TrimSpace(route.NodeID)
    destination, err := canonicalPrefix(route.Destination)
    if err != nil {
        return Route{}, err
    }
    route.Destination = destination
    route.Family = familyForPrefix(destination)
    route.Protocol = strings.ToLower(strings.TrimSpace(route.Protocol))
    route.Scope = strings.ToLower(strings.TrimSpace(route.Scope))
    route.Type = strings.ToLower(strings.TrimSpace(route.Type))
    route.Owner = normalizeOwner(route.Owner)
    for i := range route.NextHops {
        gateway, err := canonicalAddress(route.NextHops[i].Gateway)
        if err != nil {
            return Route{}, err
        }
        route.NextHops[i].Gateway = gateway
        route.NextHops[i].Interface = strings.TrimSpace(route.NextHops[i].Interface)
        if route.NextHops[i].Weight < 1 {
            route.NextHops[i].Weight = 1
        }
    }
    route.NextHops = stableNextHops(route.NextHops)
    return route, nil
}'''),
    ("func normalizeRule(rule PolicyRule)", r'''func normalizeRule(rule PolicyRule) (PolicyRule, error) {
    rule.ID = strings.TrimSpace(rule.ID)
    rule.NodeID = strings.TrimSpace(rule.NodeID)
    if rule.Source != "" {
        value, err := canonicalPrefix(rule.Source)
        if err != nil {
            return PolicyRule{}, err
        }
        rule.Source = value
    }
    if rule.Destination != "" {
        value, err := canonicalPrefix(rule.Destination)
        if err != nil {
            return PolicyRule{}, err
        }
        rule.Destination = value
    }
    rule.Family = strings.ToLower(strings.TrimSpace(rule.Family))
    rule.Action = strings.ToLower(strings.TrimSpace(rule.Action))
    rule.InputInterface = strings.TrimSpace(rule.InputInterface)
    rule.OutputInterface = strings.TrimSpace(rule.OutputInterface)
    rule.Owner = normalizeOwner(rule.Owner)
    return rule, nil
}'''),
    ("func routeIdentity(route Route)", r'''func routeIdentity(route Route) string {
    normalized, err := normalizeRoute(route)
    if err == nil {
        route = normalized
    }
    return strings.Join([]string{
        route.NodeID,
        route.Family,
        route.Destination,
        strconvI(route.Table),
        route.Type,
    }, "|")
}'''),
    ("func ruleIdentity(rule PolicyRule)", r'''func ruleIdentity(rule PolicyRule) string {
    normalized, err := normalizeRule(rule)
    if err == nil {
        rule = normalized
    }
    return strings.Join([]string{
        rule.NodeID,
        rule.Family,
        strconvI(rule.Priority),
    }, "|")
}'''),
])

controlplane = ROOT / "internal/controlplane/controlplane.go"
patch_go(controlplane, [
    ("func (c *ControlPlane) Apply(req ApplyRequest)", r'''func (c *ControlPlane) Apply(req ApplyRequest) (Transaction, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if req.PlanID == "" || strings.TrimSpace(req.IdempotencyKey) == "" {
        return Transaction{}, fmt.Errorf("plan_id and idempotency_key are required")
    }
    if existing, ok := c.idempotency[req.IdempotencyKey]; ok {
        txn, found := c.transactions[existing]
        if !found {
            return Transaction{}, fmt.Errorf("%w: idempotency record points to missing transaction", ErrConflict)
        }
        if txn.PlanID != req.PlanID {
            return Transaction{}, fmt.Errorf("%w: idempotency key already belongs to another plan", ErrConflict)
        }
        return cloneTransaction(txn), nil
    }
    plan, ok := c.plans[req.PlanID]
    if !ok {
        return Transaction{}, fmt.Errorf("%w: plan %s", ErrNotFound, req.PlanID)
    }
    if plan.BaseRevision != req.BaseRevision || plan.BaseRevision != c.desired.Revision || plan.CandidateRevision != c.desired.Revision+1 {
        return Transaction{}, fmt.Errorf("%w: stale plan base=%d request=%d current=%d", ErrConflict, plan.BaseRevision, req.BaseRevision, c.desired.Revision)
    }
    candidate := cloneDesired(c.desired)
    if err := applyRouteMutations(&candidate, plan.RouteMutations); err != nil {
        return Transaction{}, err
    }
    if err := applyRuleMutations(&candidate, plan.RuleMutations); err != nil {
        return Transaction{}, err
    }
    candidate.Revision = c.desired.Revision + 1
    candidate.UpdatedAt = time.Now().UTC()
    if err := validateDesired(candidate, c.nodes); err != nil {
        return Transaction{}, err
    }
    if _, _, err := c.managementSafety(candidate); err != nil {
        return Transaction{}, err
    }
    nodes := uniqueSorted(req.Nodes)
    if len(nodes) == 0 {
        for id := range c.nodes {
            nodes = append(nodes, id)
        }
        sort.Strings(nodes)
    }
    txn := Transaction{
        ID: transactionID(req.IdempotencyKey, plan.ID, candidate.Revision),
        PlanID: plan.ID,
        IdempotencyKey: req.IdempotencyKey,
        BaseRevision: c.desired.Revision,
        TargetRevision: candidate.Revision,
        Actor: strings.TrimSpace(req.Actor),
        Phase: TransactionCommitted,
        Nodes: map[string]NodeTransaction{},
        CreatedAt: time.Now().UTC(),
        UpdatedAt: time.Now().UTC(),
    }
    nextObserved := cloneObservedMap(c.observed)
    for _, nodeID := range nodes {
        node, found := c.nodes[nodeID]
        if !found {
            return Transaction{}, fmt.Errorf("%w: node %s", ErrNotFound, nodeID)
        }
        if !node.Online {
            return Transaction{}, fmt.Errorf("node %s is offline", nodeID)
        }
        before := cloneObserved(c.observed[nodeID])
        after := desiredForNode(candidate, nodeID)
        txn.Nodes[nodeID] = NodeTransaction{NodeID: nodeID, Before: before, After: after, Phase: TransactionCommitted}
        nextObserved[nodeID] = cloneObserved(after)
    }
    oldDesired := c.desired
    oldObserved := c.observed
    oldTransactions := c.transactions
    oldIdempotency := c.idempotency
    oldAudit := c.audit
    oldSequence := c.sequence
    c.desired = candidate
    c.observed = nextObserved
    c.transactions = cloneTransactions(c.transactions)
    c.idempotency = cloneStringMap(c.idempotency)
    c.transactions[txn.ID] = cloneTransaction(txn)
    c.idempotency[req.IdempotencyKey] = txn.ID
    c.recordAuditLocked(req.Actor, "transaction.commit", "transaction", txn.ID, candidate.Revision, map[string]any{"nodes": nodes})
    if err := c.persistLocked(); err != nil {
        c.desired = oldDesired
        c.observed = oldObserved
        c.transactions = oldTransactions
        c.idempotency = oldIdempotency
        c.audit = oldAudit
        c.sequence = oldSequence
        return Transaction{}, err
    }
    delete(c.plans, req.PlanID)
    return cloneTransaction(txn), nil
}'''),
    ("func (c *ControlPlane) Rollback(req RollbackRequest)", r'''func (c *ControlPlane) Rollback(req RollbackRequest) (Transaction, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    original, ok := c.transactions[req.TransactionID]
    if !ok {
        return Transaction{}, fmt.Errorf("%w: transaction %s", ErrNotFound, req.TransactionID)
    }
    if original.Phase != TransactionCommitted {
        return Transaction{}, fmt.Errorf("%w: transaction %s not committed", ErrConflict, req.TransactionID)
    }
    key := "rollback:" + req.TransactionID
    if existing, ok := c.idempotency[key]; ok {
        if txn, found := c.transactions[existing]; found {
            return cloneTransaction(txn), nil
        }
    }
    if c.desired.Revision != original.TargetRevision {
        return Transaction{}, fmt.Errorf("%w: rollback would overwrite newer revision %d", ErrConflict, c.desired.Revision)
    }
    candidate := cloneDesired(c.desired)
    affected := map[string]bool{}
    for nodeID := range original.Nodes {
        affected[nodeID] = true
    }
    routes := make([]Route, 0, len(candidate.Routes))
    rules := make([]PolicyRule, 0, len(candidate.Rules))
    links := make([]Link, 0, len(candidate.Links))
    for _, route := range candidate.Routes {
        if !affected[route.NodeID] { routes = append(routes, route) }
    }
    for _, rule := range candidate.Rules {
        if !affected[rule.NodeID] { rules = append(rules, rule) }
    }
    for _, link := range candidate.Links {
        if !affected[link.NodeID] { links = append(links, link) }
    }
    nextObserved := cloneObservedMap(c.observed)
    rollback := Transaction{
        ID: transactionID(key, original.PlanID, c.desired.Revision+1),
        PlanID: original.PlanID,
        IdempotencyKey: key,
        BaseRevision: c.desired.Revision,
        TargetRevision: c.desired.Revision + 1,
        Actor: strings.TrimSpace(req.Actor),
        Phase: TransactionRolledBack,
        Nodes: map[string]NodeTransaction{},
        CreatedAt: time.Now().UTC(),
        UpdatedAt: time.Now().UTC(),
    }
    for nodeID, prior := range original.Nodes {
        before := cloneObserved(c.observed[nodeID])
        restored := cloneObserved(prior.Before)
        restored.Revision = rollback.TargetRevision
        restored.CollectedAt = time.Now().UTC()
        for _, route := range restored.Routes { routes = append(routes, route) }
        for _, rule := range restored.Rules { rules = append(rules, rule) }
        for _, link := range restored.Links { links = append(links, link) }
        nextObserved[nodeID] = restored
        rollback.Nodes[nodeID] = NodeTransaction{NodeID: nodeID, Before: before, After: restored, Phase: TransactionRolledBack}
    }
    candidate.Routes = routes
    candidate.Rules = rules
    candidate.Links = links
    candidate.Revision = rollback.TargetRevision
    candidate.UpdatedAt = time.Now().UTC()
    if err := validateDesired(candidate, c.nodes); err != nil { return Transaction{}, err }
    oldDesired := c.desired
    oldObserved := c.observed
    oldTransactions := c.transactions
    oldIdempotency := c.idempotency
    oldAudit := c.audit
    oldSequence := c.sequence
    c.desired = candidate
    c.observed = nextObserved
    c.transactions = cloneTransactions(c.transactions)
    c.idempotency = cloneStringMap(c.idempotency)
    c.transactions[rollback.ID] = cloneTransaction(rollback)
    c.idempotency[key] = rollback.ID
    c.recordAuditLocked(req.Actor, "transaction.rollback", "transaction", req.TransactionID, candidate.Revision, map[string]any{"reason": req.Reason})
    if err := c.persistLocked(); err != nil {
        c.desired = oldDesired
        c.observed = oldObserved
        c.transactions = oldTransactions
        c.idempotency = oldIdempotency
        c.audit = oldAudit
        c.sequence = oldSequence
        return Transaction{}, err
    }
    return cloneTransaction(rollback), nil
}'''),
    ("func (c *ControlPlane) load()", r'''func (c *ControlPlane) load() error {
    path := filepath.Join(c.cfg.StateDir, "state.json")
    body, err := os.ReadFile(path)
    if os.IsNotExist(err) { return nil }
    if err != nil { return fmt.Errorf("read state: %w", err) }
    var state durableState
    if err := json.Unmarshal(body, &state); err != nil { return fmt.Errorf("decode state: %w", err) }
    c.desired = state.Desired
    if state.Observed != nil { c.observed = state.Observed }
    if state.Nodes != nil { c.nodes = state.Nodes }
    if state.Transactions != nil { c.transactions = state.Transactions }
    if state.Idempotency != nil { c.idempotency = state.Idempotency }
    if state.Rollouts != nil { c.rollouts = state.Rollouts }
    if state.Audit != nil { c.audit = state.Audit }
    c.sequence = state.Sequence
    for id, txn := range c.transactions {
        if txn.Phase == TransactionPrepared || txn.Phase == TransactionApplying || txn.Phase == TransactionRollingBack {
            txn.Phase = TransactionFailed
            txn.UpdatedAt = time.Now().UTC()
            c.transactions[id] = txn
        }
    }
    return nil
}'''),
    ("func (c *ControlPlane) persistLocked()", r'''func (c *ControlPlane) persistLocked() error {
    state := durableState{Desired:c.desired,Observed:c.observed,Nodes:c.nodes,Transactions:c.transactions,Idempotency:c.idempotency,Rollouts:c.rollouts,Audit:c.audit,Sequence:c.sequence}
    body, err := json.MarshalIndent(state, "", "  ")
    if err != nil { return fmt.Errorf("encode state: %w", err) }
    tmp := filepath.Join(c.cfg.StateDir, "state.json.tmp")
    dst := filepath.Join(c.cfg.StateDir, "state.json")
    if err := os.WriteFile(tmp, body, 0o600); err != nil { return fmt.Errorf("write state temp: %w", err) }
    file, err := os.OpenFile(tmp, os.O_RDWR, 0o600)
    if err != nil { return fmt.Errorf("open state temp: %w", err) }
    if err := file.Sync(); err != nil { file.Close(); return fmt.Errorf("sync state temp: %w", err) }
    if err := file.Close(); err != nil { return fmt.Errorf("close state temp: %w", err) }
    if err := os.Rename(tmp, dst); err != nil { return fmt.Errorf("publish state: %w", err) }
    dir, err := os.Open(c.cfg.StateDir)
    if err != nil { return fmt.Errorf("open state directory: %w", err) }
    defer dir.Close()
    if err := dir.Sync(); err != nil { return fmt.Errorf("sync state directory: %w", err) }
    return nil
}'''),
    ("func validateDesired(state DesiredState, nodes map[string]Node)", r'''func validateDesired(state DesiredState, nodes map[string]Node) error {
    routeIDs := map[string]bool{}
    routeKeys := map[string]string{}
    ruleIDs := map[string]bool{}
    priorities := map[string]string{}
    tables := map[string]bool{}
    for _, raw := range state.Routes {
        route, err := normalizeRoute(raw)
        if err != nil { return err }
        if route.ID == "" || route.NodeID == "" { return fmt.Errorf("route id and node_id are required") }
        if _, ok := nodes[route.NodeID]; !ok { return fmt.Errorf("%w: route %s references node %s", ErrNotFound, route.ID, route.NodeID) }
        if routeIDs[route.ID] { return fmt.Errorf("%w: duplicate route id %s", ErrConflict, route.ID) }
        routeIDs[route.ID] = true
        key := routeIdentity(route)
        if prior, ok := routeKeys[key]; ok && prior != route.ID { return fmt.Errorf("%w: routes %s and %s share effective identity", ErrConflict, prior, route.ID) }
        routeKeys[key] = route.ID
        tables[route.NodeID+"|"+strconvI(route.Table)] = true
    }
    for _, raw := range state.Rules {
        rule, err := normalizeRule(raw)
        if err != nil { return err }
        if rule.ID == "" || rule.NodeID == "" { return fmt.Errorf("rule id and node_id are required") }
        if _, ok := nodes[rule.NodeID]; !ok { return fmt.Errorf("%w: rule %s references node %s", ErrNotFound, rule.ID, rule.NodeID) }
        if ruleIDs[rule.ID] { return fmt.Errorf("%w: duplicate rule id %s", ErrConflict, rule.ID) }
        ruleIDs[rule.ID] = true
        key := ruleIdentity(rule)
        if prior, ok := priorities[key]; ok && prior != rule.ID { return fmt.Errorf("%w: rules %s and %s share effective priority", ErrConflict, prior, rule.ID) }
        priorities[key] = rule.ID
        if rule.Action == "lookup" && !tables[rule.NodeID+"|"+strconvI(rule.Table)] {
            return fmt.Errorf("rule %s references absent table %d", rule.ID, rule.Table)
        }
    }
    return nil
}'''),
])

# Add a helper used by atomic transaction updates if it is not already present.
text = controlplane.read_text()
if "func cloneStringMap(" not in text:
    text += r'''

func cloneStringMap(in map[string]string) map[string]string {
    out := make(map[string]string, len(in))
    for k, v := range in { out[k] = v }
    return out
}
'''
controlplane.write_text(text)

# Drift: ownership is normalized and reconciliation must be based on a fresh observation.
drift = ROOT / "internal/controlplane/drift.go"
patch_go(drift, [
    ("func (c *ControlPlane) Reconcile(req ReconcileRequest)", r'''func (c *ControlPlane) Reconcile(req ReconcileRequest) (ReconcileResult, error) {
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
    if observed.Revision != c.desired.Revision {
        return ReconcileResult{}, fmt.Errorf("%w: observed snapshot revision %d is stale versus desired %d", ErrConflict, observed.Revision, c.desired.Revision)
    }
    drift := c.driftLocked(req.NodeID)
    actionable := make([]DriftItem, 0, len(drift))
    for _, item := range drift {
        if item.Kind == DriftUnexpected && !item.Owned { continue }
        actionable = append(actionable, item)
    }
    result := ReconcileResult{NodeID:req.NodeID, Drift:actionable}
    if req.DryRun || len(actionable) == 0 { return result, nil }
    key := fmt.Sprintf("reconcile:%s:%d", req.NodeID, observed.Revision)
    if existing, ok := c.idempotency[key]; ok {
        result.Applied = true
        result.TransactionID = existing
        return result, nil
    }
    before := cloneObserved(observed)
    after := desiredForNode(c.desired, req.NodeID)
    txn := Transaction{ID:transactionID(key,"reconcile",c.desired.Revision),PlanID:"reconcile",IdempotencyKey:key,BaseRevision:observed.Revision,TargetRevision:c.desired.Revision,Actor:req.Actor,Phase:TransactionCommitted,Nodes:map[string]NodeTransaction{req.NodeID:{NodeID:req.NodeID,Before:before,After:after,Phase:TransactionCommitted}},CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()}
    oldObserved := c.observed
    oldTransactions := c.transactions
    oldIdempotency := c.idempotency
    oldAudit := c.audit
    oldSequence := c.sequence
    c.observed = cloneObservedMap(c.observed)
    c.transactions = cloneTransactions(c.transactions)
    c.idempotency = cloneStringMap(c.idempotency)
    c.observed[req.NodeID] = after
    c.transactions[txn.ID] = txn
    c.idempotency[key] = txn.ID
    c.recordAuditLocked(req.Actor,"reconcile.commit","node",req.NodeID,c.desired.Revision,map[string]any{"drift_items":len(actionable)})
    if err := c.persistLocked(); err != nil {
        c.observed = oldObserved; c.transactions = oldTransactions; c.idempotency = oldIdempotency; c.audit = oldAudit; c.sequence = oldSequence
        return ReconcileResult{}, err
    }
    result.Applied = true
    result.TransactionID = txn.ID
    return result, nil
}'''),
])

# Rollout: heartbeat freshness, deterministic retry identity, canary isolation, and no replay at target revision.
rollout = ROOT / "internal/controlplane/rollout.go"
patch_go(rollout, [
    ("func (c *ControlPlane) Rollout(req RolloutRequest)", r'''func (c *ControlPlane) Rollout(req RolloutRequest) (Rollout, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if req.Revision == 0 { req.Revision = c.desired.Revision }
    if req.Revision != c.desired.Revision { return Rollout{}, fmt.Errorf("%w: rollout revision %d is not current %d", ErrConflict, req.Revision, c.desired.Revision) }
    if req.WaveSize < 1 { req.WaveSize = 5 }
    if req.WaveSize > c.cfg.MaxWave { return Rollout{}, fmt.Errorf("wave_size %d exceeds maximum %d", req.WaveSize, c.cfg.MaxWave) }
    selected := c.selectNodesLocked(req.Selector)
    if len(selected) == 0 { return Rollout{}, fmt.Errorf("no nodes match selector") }
    canaries := uniqueSorted(req.CanaryNodes)
    selectedSet := map[string]bool{}
    for _, id := range selected { selectedSet[id] = true }
    for _, id := range canaries { if !selectedSet[id] { return Rollout{}, fmt.Errorf("canary %s is outside selector", id) } }
    id := rolloutID(req)
    if existing, ok := c.rollouts[id]; ok && existing.Status == "succeeded" {
        return cloneRollout(existing), nil
    }
    ordered := make([]string, 0, len(selected))
    seen := map[string]bool{}
    for _, id := range canaries { if !seen[id] { seen[id] = true; ordered = append(ordered, id) } }
    for _, id := range selected { if !seen[id] { seen[id] = true; ordered = append(ordered, id) } }
    waves := make([]RolloutWave, 0)
    offset := 0
    if len(canaries) > 0 {
        nodes := make([]RolloutNode, 0, len(canaries))
        for _, nodeID := range canaries { nodes = append(nodes, RolloutNode{NodeID:nodeID,Revision:req.Revision,Status:"pending"}) }
        waves = append(waves, RolloutWave{Index:0,Nodes:nodes,Status:"pending"})
        offset = len(canaries)
    }
    for offset < len(ordered) {
        end := offset + req.WaveSize
        if end > len(ordered) { end = len(ordered) }
        nodes := make([]RolloutNode, 0, end-offset)
        for _, nodeID := range ordered[offset:end] { nodes = append(nodes, RolloutNode{NodeID:nodeID,Revision:req.Revision,Status:"pending"}) }
        waves = append(waves, RolloutWave{Index:len(waves),Nodes:nodes,Status:"pending"})
        offset = end
    }
    now := time.Now().UTC()
    ro := Rollout{ID:id,Revision:req.Revision,Selector:cloneLabels(req.Selector),Actor:req.Actor,Waves:waves,Status:"running",CreatedAt:now,UpdatedAt:now}
    c.rollouts[id] = cloneRollout(ro)
    c.recordAuditLocked(req.Actor,"rollout.start","rollout",id,req.Revision,map[string]any{"waves":len(waves),"nodes":len(selected)})
    if err := c.persistLocked(); err != nil { return Rollout{}, err }
    for wi := range ro.Waves {
        wave := ro.Waves[wi]
        wave.Status = "running"
        for ni := range wave.Nodes {
            result := wave.Nodes[ni]
            node := c.nodes[result.NodeID]
            if !node.Online || node.HeartbeatAt.IsZero() || time.Since(node.HeartbeatAt) > 2*time.Minute {
                result.Status = "failed"; result.Error = "node heartbeat is offline or stale"; wave.Nodes[ni] = result; wave.Status = "failed"; ro.Status = "failed"; ro.Waves[wi] = wave; ro.UpdatedAt = time.Now().UTC(); c.rollouts[id] = cloneRollout(ro); c.recordAuditLocked(req.Actor,"rollout.node_failed","node",result.NodeID,req.Revision,map[string]any{"reason":"heartbeat","wave":wi}); _ = c.persistLocked(); return cloneRollout(ro), nil
            }
            observed := c.observed[result.NodeID]
            if observed.Revision == req.Revision {
                result.Status = "already_current"; wave.Nodes[ni] = result; continue
            }
            before := cloneObserved(observed)
            after := desiredForNode(c.desired,result.NodeID)
            key := "rollout:"+id+":"+result.NodeID
            txn := Transaction{ID:transactionID(key,"rollout",req.Revision),PlanID:"rollout",IdempotencyKey:key,BaseRevision:before.Revision,TargetRevision:req.Revision,Actor:req.Actor,Phase:TransactionCommitted,Nodes:map[string]NodeTransaction{result.NodeID:{NodeID:result.NodeID,Before:before,After:after,Phase:TransactionCommitted}},CreatedAt:time.Now().UTC(),UpdatedAt:time.Now().UTC()}
            c.observed[result.NodeID] = after
            c.transactions[txn.ID] = txn
            c.idempotency[key] = txn.ID
            result.Status = "succeeded"; wave.Nodes[ni] = result
            c.recordAuditLocked(req.Actor,"rollout.node_succeeded","node",result.NodeID,req.Revision,map[string]any{"wave":wi,"transaction_id":txn.ID})
        }
        wave.Status = "succeeded"
        ro.Waves[wi] = wave
        ro.UpdatedAt = time.Now().UTC()
        c.rollouts[id] = cloneRollout(ro)
        if err := c.persistLocked(); err != nil { return Rollout{}, err }
    }
    ro.Status = "succeeded"; ro.UpdatedAt = time.Now().UTC(); c.rollouts[id] = cloneRollout(ro); c.recordAuditLocked(req.Actor,"rollout.complete","rollout",id,req.Revision,map[string]any{"status":ro.Status})
    if err := c.persistLocked(); err != nil { return Rollout{}, err }
    return cloneRollout(ro), nil
}'''),
])

# Dashboard binds Apply to the exact preview revision, not a mutable background-refresh value.
web = ROOT / "web/app.ts"
web_text = web.read_text()
web_text = web_text.replace("}) as {id: string};\n      await this.api.apply({\n        plan_id: plan.id,\n        base_revision: this.revision,", "}) as {id: string; base_revision: number};\n      await this.api.apply({\n        plan_id: plan.id,\n        base_revision: plan.base_revision,")
web.write_text(web_text)

# Ansible uses a stable projected config and makes host-specific protected routes explicit inputs.
defaults = ROOT / "ansible/roles/routecp/defaults/main.yml"
default_text = defaults.read_text()
if "routecp_protected_routes:" not in default_text:
    default_text += "\nroutecp_protected_routes: []\nroutecp_host_routes: []\n"
defaults.write_text(default_text)

tasks = ROOT / "ansible/roles/routecp/tasks/main.yml"
task_text = tasks.read_text()
task_text = task_text.replace("'routes': routecp_routes,", "'routes': ((routecp_routes | default([])) + (routecp_protected_routes | default([])) + (routecp_host_routes | default([]))),")
tasks.write_text(task_text)

print("route-control-plane reference repairs installed")
