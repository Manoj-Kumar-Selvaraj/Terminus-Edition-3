package controlplane

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "net/netip"
    "os"
    "path/filepath"
    "sort"
    "strings"
    "sync"
    "time"
)

type ControlPlane struct {
    mu sync.RWMutex
    cfg Config
    desired DesiredState
    observed map[string]ObservedState
    nodes map[string]Node
    plans map[string]Plan
    transactions map[string]Transaction
    idempotency map[string]string
    rollouts map[string]Rollout
    audit []AuditEvent
    sequence uint64
}

type durableState struct {
    Desired DesiredState `json:"desired"`
    Observed map[string]ObservedState `json:"observed"`
    Nodes map[string]Node `json:"nodes"`
    Transactions map[string]Transaction `json:"transactions"`
    Idempotency map[string]string `json:"idempotency"`
    Rollouts map[string]Rollout `json:"rollouts"`
    Audit []AuditEvent `json:"audit"`
    Sequence uint64 `json:"sequence"`
}

func Open(cfg Config) (*ControlPlane, error) {
    if cfg.MaxWave < 1 {
        cfg.MaxWave = 25
    }
    if cfg.StateDir == "" {
        cfg.StateDir = "/app/routecp/state"
    }
    cp := &ControlPlane{
        cfg: cfg,
        observed: map[string]ObservedState{},
        nodes: map[string]Node{},
        plans: map[string]Plan{},
        transactions: map[string]Transaction{},
        idempotency: map[string]string{},
        rollouts: map[string]Rollout{},
        audit: []AuditEvent{},
    }
    if err := os.MkdirAll(cfg.StateDir, 0o755); err != nil {
        return nil, fmt.Errorf("create state directory: %w", err)
    }
    if err := cp.load(); err != nil {
        return nil, err
    }
    return cp, nil
}

func (c *ControlPlane) Revision() uint64 {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.desired.Revision
}

func (c *ControlPlane) Snapshot() Snapshot {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return Snapshot{
        Desired: cloneDesired(c.desired),
        Observed: cloneObservedMap(c.observed),
        Nodes: cloneNodeMap(c.nodes),
        Transactions: cloneTransactions(c.transactions),
        Rollouts: cloneRollouts(c.rollouts),
    }
}

func (c *ControlPlane) Nodes() []Node {
    c.mu.RLock()
    defer c.mu.RUnlock()
    out := make([]Node, 0, len(c.nodes))
    for _, node := range c.nodes {
        out = append(out, cloneNode(node))
    }
    sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
    return out
}

func (c *ControlPlane) UpsertNode(node Node) error {
    node.ID = strings.TrimSpace(node.ID)
    node.Hostname = strings.TrimSpace(node.Hostname)
    node.Site = strings.TrimSpace(node.Site)
    node.Environment = strings.TrimSpace(node.Environment)
    node.ManagementIP = strings.TrimSpace(node.ManagementIP)
    if node.ID == "" || node.Hostname == "" || node.ManagementIP == "" {
        return fmt.Errorf("node id, hostname and management_ip are required")
    }
    if _, err := canonicalAddress(node.ManagementIP); err != nil {
        return err
    }
    c.mu.Lock()
    defer c.mu.Unlock()
    node.HeartbeatAt = time.Now().UTC()
    c.nodes[node.ID] = cloneNode(node)
    if _, ok := c.observed[node.ID]; !ok {
        c.observed[node.ID] = ObservedState{Revision: c.desired.Revision, CollectedAt: time.Now().UTC()}
    }
    c.recordAuditLocked(node.ID, "node.upsert", "node", node.ID, c.desired.Revision, map[string]any{"online": node.Online})
    return c.persistLocked()
}

func (c *ControlPlane) Routes(nodeID, table string) []Route {
    c.mu.RLock()
    defer c.mu.RUnlock()
    var tableNumber int
    if table != "" {
        fmt.Sscanf(table, "%d", &tableNumber)
    }
    out := make([]Route, 0)
    for _, route := range c.desired.Routes {
        if nodeID != "" && route.NodeID != nodeID {
            continue
        }
        if table != "" && route.Table != tableNumber {
            continue
        }
        out = append(out, cloneRoute(route))
    }
    sort.Slice(out, func(i, j int) bool {
        if out[i].NodeID != out[j].NodeID { return out[i].NodeID < out[j].NodeID }
        if out[i].Table != out[j].Table { return out[i].Table < out[j].Table }
        if out[i].Destination != out[j].Destination { return out[i].Destination < out[j].Destination }
        return out[i].Metric < out[j].Metric
    })
    return out
}

func (c *ControlPlane) Preview(req ChangeRequest) (Plan, error) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    if req.BaseRevision != c.desired.Revision {
        return Plan{}, fmt.Errorf("%w: base revision %d does not match current %d", ErrConflict, req.BaseRevision, c.desired.Revision)
    }
    candidate := cloneDesired(c.desired)
    if err := applyRouteMutations(&candidate, req.RouteMutations); err != nil {
        return Plan{}, err
    }
    if err := applyRuleMutations(&candidate, req.RuleMutations); err != nil {
        return Plan{}, err
    }
    if err := validateDesired(candidate, c.nodes); err != nil {
        return Plan{}, err
    }
    warnings, protected, err := c.managementSafety(candidate)
    if err != nil {
        return Plan{}, err
    }
    plan := Plan{
        BaseRevision: req.BaseRevision,
        CandidateRevision: req.BaseRevision + 1,
        Actor: strings.TrimSpace(req.Actor),
        Reason: strings.TrimSpace(req.Reason),
        RouteMutations: cloneRouteMutations(req.RouteMutations),
        RuleMutations: cloneRuleMutations(req.RuleMutations),
        Warnings: warnings,
        ProtectedPaths: protected,
        CreatedAt: time.Now().UTC(),
    }
    plan.ID = planHash(plan)
    c.plans[plan.ID] = plan
    return plan, nil
}

func (c *ControlPlane) Apply(req ApplyRequest) (Transaction, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if req.PlanID == "" || req.IdempotencyKey == "" {
        return Transaction{}, fmt.Errorf("plan_id and idempotency_key are required")
    }
    if existing, ok := c.idempotency[req.IdempotencyKey]; ok {
        if txn, found := c.transactions[existing]; found {
            return cloneTransaction(txn), nil
        }
    }
    plan, ok := c.plans[req.PlanID]
    if !ok {
        return Transaction{}, fmt.Errorf("%w: plan %s", ErrNotFound, req.PlanID)
    }
    if req.BaseRevision != c.desired.Revision {
        return Transaction{}, fmt.Errorf("%w: stale apply base=%d current=%d", ErrConflict, req.BaseRevision, c.desired.Revision)
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
        for id := range c.nodes { nodes = append(nodes, id) }
        sort.Strings(nodes)
    }
    txn := Transaction{
        ID: transactionID(req.IdempotencyKey, plan.ID, candidate.Revision),
        PlanID: plan.ID,
        IdempotencyKey: req.IdempotencyKey,
        BaseRevision: c.desired.Revision,
        TargetRevision: candidate.Revision,
        Actor: req.Actor,
        Phase: TransactionPrepared,
        Nodes: map[string]NodeTransaction{},
        CreatedAt: time.Now().UTC(),
        UpdatedAt: time.Now().UTC(),
    }
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
        txn.Nodes[nodeID] = NodeTransaction{NodeID: nodeID, Before: before, After: after, Phase: TransactionPrepared}
    }
    c.transactions[txn.ID] = cloneTransaction(txn)
    c.idempotency[req.IdempotencyKey] = txn.ID
    c.recordAuditLocked(req.Actor, "transaction.prepare", "transaction", txn.ID, candidate.Revision, map[string]any{"nodes": nodes})
    if err := c.persistLocked(); err != nil { return Transaction{}, err }
    txn.Phase = TransactionApplying
    txn.UpdatedAt = time.Now().UTC()
    c.transactions[txn.ID] = cloneTransaction(txn)
    for _, nodeID := range nodes {
        nt := txn.Nodes[nodeID]
        nt.Phase = TransactionApplying
        txn.Nodes[nodeID] = nt
        c.observed[nodeID] = cloneObserved(nt.After)
        nt.Phase = TransactionCommitted
        txn.Nodes[nodeID] = nt
    }
    c.desired = candidate
    txn.Phase = TransactionCommitted
    txn.UpdatedAt = time.Now().UTC()
    c.transactions[txn.ID] = cloneTransaction(txn)
    c.recordAuditLocked(req.Actor, "transaction.commit", "transaction", txn.ID, candidate.Revision, map[string]any{"nodes": nodes})
    if err := c.persistLocked(); err != nil { return Transaction{}, err }
    return cloneTransaction(txn), nil
}

func (c *ControlPlane) Rollback(req RollbackRequest) (Transaction, error) {
    c.mu.Lock()
    defer c.mu.Unlock()
    original, ok := c.transactions[req.TransactionID]
    if !ok {
        return Transaction{}, fmt.Errorf("%w: transaction %s", ErrNotFound, req.TransactionID)
    }
    if original.Phase != TransactionCommitted {
        return Transaction{}, fmt.Errorf("%w: transaction %s not committed", ErrConflict, req.TransactionID)
    }
    rollback := Transaction{
        ID: transactionID("rollback:"+req.TransactionID, original.PlanID, original.BaseRevision),
        PlanID: original.PlanID,
        IdempotencyKey: "rollback:" + req.TransactionID,
        BaseRevision: c.desired.Revision,
        TargetRevision: original.BaseRevision,
        Actor: req.Actor,
        Phase: TransactionRollingBack,
        Nodes: map[string]NodeTransaction{},
        CreatedAt: time.Now().UTC(),
        UpdatedAt: time.Now().UTC(),
    }
    for nodeID, old := range original.Nodes {
        current := cloneObserved(c.observed[nodeID])
        rollback.Nodes[nodeID] = NodeTransaction{NodeID: nodeID, Before: current, After: old.Before, Phase: TransactionRollingBack}
        c.observed[nodeID] = cloneObserved(old.Before)
        nt := rollback.Nodes[nodeID]
        nt.Phase = TransactionRolledBack
        rollback.Nodes[nodeID] = nt
    }
    rollback.Phase = TransactionRolledBack
    rollback.UpdatedAt = time.Now().UTC()
    c.transactions[rollback.ID] = cloneTransaction(rollback)
    c.idempotency[rollback.IdempotencyKey] = rollback.ID
    c.recordAuditLocked(req.Actor, "transaction.rollback", "transaction", req.TransactionID, original.BaseRevision, map[string]any{"reason": req.Reason})
    if err := c.persistLocked(); err != nil { return Transaction{}, err }
    return cloneTransaction(rollback), nil
}

func (c *ControlPlane) Audit(limit int) []AuditEvent {
    c.mu.RLock()
    defer c.mu.RUnlock()
    if limit <= 0 || limit > len(c.audit) { limit = len(c.audit) }
    start := len(c.audit) - limit
    out := make([]AuditEvent, limit)
    copy(out, c.audit[start:])
    return out
}

func (c *ControlPlane) load() error {
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
    return nil
}

func (c *ControlPlane) persistLocked() error {
    state := durableState{
        Desired: c.desired,
        Observed: c.observed,
        Nodes: c.nodes,
        Transactions: c.transactions,
        Idempotency: c.idempotency,
        Rollouts: c.rollouts,
        Audit: c.audit,
        Sequence: c.sequence,
    }
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
    return nil
}

func (c *ControlPlane) recordAuditLocked(actor, action, objectType, objectID string, revision uint64, detail map[string]any) {
    c.sequence++
    c.audit = append(c.audit, AuditEvent{Sequence: c.sequence, Time: time.Now().UTC(), Actor: actor, Action: action, ObjectType: objectType, ObjectID: objectID, Revision: revision, Detail: detail})
    if len(c.audit) > 10000 { c.audit = append([]AuditEvent(nil), c.audit[len(c.audit)-10000:]...) }
}

func applyRouteMutations(state *DesiredState, mutations []RouteMutation) error {
    routes := append([]Route(nil), state.Routes...)
    for _, mutation := range mutations {
        normalized, err := normalizeRoute(mutation.Route)
        if err != nil { return err }
        switch strings.ToLower(strings.TrimSpace(mutation.Operation)) {
        case "add":
            for _, existing := range routes {
                if routeIdentity(existing) == routeIdentity(normalized) { return fmt.Errorf("%w: duplicate route", ErrConflict) }
            }
            routes = append(routes, normalized)
        case "replace":
            replaced := false
            for i := range routes {
                if routes[i].ID == normalized.ID {
                    routes[i] = normalized
                    replaced = true
                    break
                }
            }
            if !replaced { return fmt.Errorf("%w: route %s", ErrNotFound, normalized.ID) }
        case "delete":
            filtered := routes[:0]
            found := false
            for _, existing := range routes {
                if existing.ID == normalized.ID { found = true; continue }
                filtered = append(filtered, existing)
            }
            if !found { return fmt.Errorf("%w: route %s", ErrNotFound, normalized.ID) }
            routes = filtered
        default:
            return fmt.Errorf("unknown route operation %q", mutation.Operation)
        }
    }
    state.Routes = routes
    return nil
}

func applyRuleMutations(state *DesiredState, mutations []RuleMutation) error {
    rules := append([]PolicyRule(nil), state.Rules...)
    for _, mutation := range mutations {
        normalized, err := normalizeRule(mutation.Rule)
        if err != nil { return err }
        switch strings.ToLower(strings.TrimSpace(mutation.Operation)) {
        case "add":
            for _, existing := range rules {
                if ruleIdentity(existing) == ruleIdentity(normalized) { return fmt.Errorf("%w: duplicate rule", ErrConflict) }
            }
            rules = append(rules, normalized)
        case "replace":
            replaced := false
            for i := range rules {
                if rules[i].ID == normalized.ID { rules[i] = normalized; replaced = true; break }
            }
            if !replaced { return fmt.Errorf("%w: rule %s", ErrNotFound, normalized.ID) }
        case "delete":
            filtered := rules[:0]
            found := false
            for _, existing := range rules {
                if existing.ID == normalized.ID { found = true; continue }
                filtered = append(filtered, existing)
            }
            if !found { return fmt.Errorf("%w: rule %s", ErrNotFound, normalized.ID) }
            rules = filtered
        default:
            return fmt.Errorf("unknown rule operation %q", mutation.Operation)
        }
    }
    state.Rules = rules
    return nil
}

func validateDesired(state DesiredState, nodes map[string]Node) error {
    priorities := map[string]string{}
    tables := map[string]bool{}
    routeIDs := map[string]bool{}
    ruleIDs := map[string]bool{}
    for _, route := range state.Routes {
        if route.ID == "" { return fmt.Errorf("route id is required") }
        if routeIDs[route.ID] { return fmt.Errorf("%w: duplicate route id %s", ErrConflict, route.ID) }
        routeIDs[route.ID] = true
        if _, ok := nodes[route.NodeID]; !ok { return fmt.Errorf("%w: route node %s", ErrNotFound, route.NodeID) }
        if route.Table < 1 { return fmt.Errorf("route %s has invalid table", route.ID) }
        if len(route.NextHops) == 0 && route.Type != "blackhole" { return fmt.Errorf("route %s has no next hop", route.ID) }
        tables[route.NodeID+"|"+strconvI(route.Table)] = true
    }
    for _, rule := range state.Rules {
        if rule.ID == "" { return fmt.Errorf("rule id is required") }
        if ruleIDs[rule.ID] { return fmt.Errorf("%w: duplicate rule id %s", ErrConflict, rule.ID) }
        ruleIDs[rule.ID] = true
        if _, ok := nodes[rule.NodeID]; !ok { return fmt.Errorf("%w: rule node %s", ErrNotFound, rule.NodeID) }
        key := rule.NodeID+"|"+strconvI(rule.Priority)
        if other, ok := priorities[key]; ok { return fmt.Errorf("%w: rule priorities collide %s and %s", ErrConflict, other, rule.ID) }
        priorities[key] = rule.ID
        if rule.Action == "lookup" && !tables[rule.NodeID+"|"+strconvI(rule.Table)] { return fmt.Errorf("rule %s references absent table %d", rule.ID, rule.Table) }
    }
    return nil
}

func (c *ControlPlane) managementSafety(candidate DesiredState) ([]string, []string, error) {
    warnings := []string{}
    protected := []string{}
    for nodeID, node := range c.nodes {
        if !node.Online { warnings = append(warnings, "node "+nodeID+" is offline") }
        management, err := canonicalAddress(node.ManagementIP)
        if err != nil { return nil, nil, err }
        reachable := false
        for _, route := range candidate.Routes {
            if route.NodeID != nodeID { continue }
            prefix, err := canonicalPrefix(route.Destination)
            if err != nil { continue }
            if prefixContains(prefix, management) {
                reachable = true
                protected = append(protected, nodeID+":"+prefix)
                break
            }
        }
        if !reachable { return nil, nil, fmt.Errorf("%w: no management route for node %s", ErrUnsafe, nodeID) }
    }
    sort.Strings(protected)
    return warnings, protected, nil
}

func prefixContains(prefixValue, addressValue string) bool {
    prefix, err := netipParsePrefix(prefixValue)
    if err != nil { return false }
    addr, err := netipParseAddr(addressValue)
    if err != nil { return false }
    return prefix.Contains(addr)
}

func desiredForNode(state DesiredState, nodeID string) ObservedState {
    observed := ObservedState{Revision: state.Revision, CollectedAt: time.Now().UTC()}
    for _, route := range state.Routes { if route.NodeID == nodeID { observed.Routes = append(observed.Routes, cloneRoute(route)) } }
    for _, rule := range state.Rules { if rule.NodeID == nodeID { observed.Rules = append(observed.Rules, rule) } }
    for _, link := range state.Links { if link.NodeID == nodeID { observed.Links = append(observed.Links, cloneLink(link)) } }
    return observed
}

func planHash(plan Plan) string {
    body, _ := json.Marshal(struct{ Base uint64; Routes []RouteMutation; Rules []RuleMutation }{plan.BaseRevision, plan.RouteMutations, plan.RuleMutations})
    sum := sha256.Sum256(body)
    return hex.EncodeToString(sum[:16])
}

func transactionID(key, plan string, revision uint64) string {
    sum := sha256.Sum256([]byte(fmt.Sprintf("%s|%s|%d", key, plan, revision)))
    return hex.EncodeToString(sum[:16])
}

func uniqueSorted(values []string) []string {
    seen := map[string]bool{}
    out := make([]string, 0, len(values))
    for _, value := range values { value = strings.TrimSpace(value); if value != "" && !seen[value] { seen[value] = true; out = append(out, value) } }
    sort.Strings(out)
    return out
}

func cloneDesired(in DesiredState) DesiredState { out := in; out.Routes = cloneRoutes(in.Routes); out.Rules = append([]PolicyRule(nil), in.Rules...); out.Links = cloneLinks(in.Links); return out }
func cloneObserved(in ObservedState) ObservedState { out := in; out.Routes = cloneRoutes(in.Routes); out.Rules = append([]PolicyRule(nil), in.Rules...); out.Links = cloneLinks(in.Links); return out }
func cloneRoute(in Route) Route { out := in; out.NextHops = append([]NextHop(nil), in.NextHops...); return out }
func cloneRoutes(in []Route) []Route { out := make([]Route, len(in)); for i := range in { out[i] = cloneRoute(in[i]) }; return out }
func cloneLink(in Link) Link { out := in; out.Addresses = append([]string(nil), in.Addresses...); return out }
func cloneLinks(in []Link) []Link { out := make([]Link, len(in)); for i := range in { out[i] = cloneLink(in[i]) }; return out }
func cloneNode(in Node) Node { out := in; if in.Labels != nil { out.Labels = map[string]string{}; for k,v := range in.Labels { out.Labels[k]=v } }; return out }
func cloneNodeMap(in map[string]Node) map[string]Node { out := map[string]Node{}; for k,v := range in { out[k]=cloneNode(v) }; return out }
func cloneObservedMap(in map[string]ObservedState) map[string]ObservedState { out := map[string]ObservedState{}; for k,v := range in { out[k]=cloneObserved(v) }; return out }
func cloneRouteMutations(in []RouteMutation) []RouteMutation { out:=make([]RouteMutation,len(in)); for i,v:=range in { out[i]=v; out[i].Route=cloneRoute(v.Route) }; return out }
func cloneRuleMutations(in []RuleMutation) []RuleMutation { return append([]RuleMutation(nil), in...) }
func cloneTransaction(in Transaction) Transaction { out:=in; out.Nodes=map[string]NodeTransaction{}; for k,v:=range in.Nodes { v.Before=cloneObserved(v.Before); v.After=cloneObserved(v.After); out.Nodes[k]=v }; return out }
func cloneTransactions(in map[string]Transaction) map[string]Transaction { out:=map[string]Transaction{}; for k,v:=range in { out[k]=cloneTransaction(v) }; return out }
func cloneRollouts(in map[string]Rollout) map[string]Rollout { out:=map[string]Rollout{}; for k,v:=range in { out[k]=cloneRollout(v) }; return out }

func netipParsePrefix(value string) (netip.Prefix,error) { return netip.ParsePrefix(value) }
func netipParseAddr(value string) (netip.Addr,error) { return netip.ParseAddr(value) }
