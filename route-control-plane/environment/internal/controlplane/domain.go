package controlplane

import (
    "errors"
    "fmt"
    "net/netip"
    "sort"
    "strings"
    "time"
)

var (
    ErrConflict = errors.New("conflict")
    ErrUnsafe = errors.New("unsafe change")
    ErrNotFound = errors.New("not found")
)

type Config struct {
    StateDir string
    ProtectedCIDRs []string
    MaxWave int
}

func DefaultConfig() Config {
    return Config{
        StateDir: "/app/routecp/state",
        ProtectedCIDRs: []string{"10.0.0.0/8", "172.16.0.0/12"},
        MaxWave: 25,
    }
}

type Node struct {
    ID string `json:"id"`
    Hostname string `json:"hostname"`
    Site string `json:"site"`
    Environment string `json:"environment"`
    ManagementIP string `json:"management_ip"`
    Online bool `json:"online"`
    HeartbeatRevision uint64 `json:"heartbeat_revision"`
    HeartbeatAt time.Time `json:"heartbeat_at"`
    Labels map[string]string `json:"labels"`
}

type NextHop struct {
    Gateway string `json:"gateway"`
    Interface string `json:"interface"`
    Weight int `json:"weight"`
}

type Route struct {
    ID string `json:"id"`
    NodeID string `json:"node_id"`
    Family string `json:"family"`
    Destination string `json:"destination"`
    Table int `json:"table"`
    Metric int `json:"metric"`
    Protocol string `json:"protocol"`
    Scope string `json:"scope"`
    Type string `json:"type"`
    NextHops []NextHop `json:"next_hops"`
    Owner string `json:"owner"`
}

type PolicyRule struct {
    ID string `json:"id"`
    NodeID string `json:"node_id"`
    Family string `json:"family"`
    Priority int `json:"priority"`
    Source string `json:"source"`
    Destination string `json:"destination"`
    Mark int `json:"mark"`
    Mask int `json:"mask"`
    InputInterface string `json:"input_interface"`
    OutputInterface string `json:"output_interface"`
    Table int `json:"table"`
    Action string `json:"action"`
    Owner string `json:"owner"`
}

type Link struct {
    NodeID string `json:"node_id"`
    Name string `json:"name"`
    Index int `json:"index"`
    Up bool `json:"up"`
    Addresses []string `json:"addresses"`
}

type DesiredState struct {
    Revision uint64 `json:"revision"`
    Routes []Route `json:"routes"`
    Rules []PolicyRule `json:"rules"`
    Links []Link `json:"links"`
    UpdatedAt time.Time `json:"updated_at"`
}

type ObservedState struct {
    Revision uint64 `json:"revision"`
    Routes []Route `json:"routes"`
    Rules []PolicyRule `json:"rules"`
    Links []Link `json:"links"`
    CollectedAt time.Time `json:"collected_at"`
}

type Snapshot struct {
    Desired DesiredState `json:"desired"`
    Observed map[string]ObservedState `json:"observed"`
    Nodes map[string]Node `json:"nodes"`
    Transactions map[string]Transaction `json:"transactions"`
    Rollouts map[string]Rollout `json:"rollouts"`
}

type RouteMutation struct {
    Operation string `json:"operation"`
    Route Route `json:"route"`
}

type RuleMutation struct {
    Operation string `json:"operation"`
    Rule PolicyRule `json:"rule"`
}

type ChangeRequest struct {
    BaseRevision uint64 `json:"base_revision"`
    Actor string `json:"actor"`
    Reason string `json:"reason"`
    RouteMutations []RouteMutation `json:"route_mutations"`
    RuleMutations []RuleMutation `json:"rule_mutations"`
}

type Plan struct {
    ID string `json:"id"`
    BaseRevision uint64 `json:"base_revision"`
    CandidateRevision uint64 `json:"candidate_revision"`
    Actor string `json:"actor"`
    Reason string `json:"reason"`
    RouteMutations []RouteMutation `json:"route_mutations"`
    RuleMutations []RuleMutation `json:"rule_mutations"`
    Warnings []string `json:"warnings"`
    ProtectedPaths []string `json:"protected_paths"`
    CreatedAt time.Time `json:"created_at"`
}

type ApplyRequest struct {
    PlanID string `json:"plan_id"`
    BaseRevision uint64 `json:"base_revision"`
    IdempotencyKey string `json:"idempotency_key"`
    Nodes []string `json:"nodes"`
    Actor string `json:"actor"`
}

type RollbackRequest struct {
    TransactionID string `json:"transaction_id"`
    Actor string `json:"actor"`
    Reason string `json:"reason"`
}

type TransactionPhase string

const (
    TransactionPrepared TransactionPhase = "prepared"
    TransactionApplying TransactionPhase = "applying"
    TransactionCommitted TransactionPhase = "committed"
    TransactionRollingBack TransactionPhase = "rolling_back"
    TransactionRolledBack TransactionPhase = "rolled_back"
    TransactionFailed TransactionPhase = "failed"
)

type NodeTransaction struct {
    NodeID string `json:"node_id"`
    Before ObservedState `json:"before"`
    After ObservedState `json:"after"`
    Phase TransactionPhase `json:"phase"`
    Error string `json:"error"`
}

type Transaction struct {
    ID string `json:"id"`
    PlanID string `json:"plan_id"`
    IdempotencyKey string `json:"idempotency_key"`
    BaseRevision uint64 `json:"base_revision"`
    TargetRevision uint64 `json:"target_revision"`
    Actor string `json:"actor"`
    Phase TransactionPhase `json:"phase"`
    Nodes map[string]NodeTransaction `json:"nodes"`
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
}

type DriftKind string

const (
    DriftMissing DriftKind = "missing"
    DriftUnexpected DriftKind = "unexpected"
    DriftChanged DriftKind = "changed"
)

type DriftItem struct {
    NodeID string `json:"node_id"`
    Kind DriftKind `json:"kind"`
    ObjectType string `json:"object_type"`
    ObjectID string `json:"object_id"`
    Desired any `json:"desired"`
    Observed any `json:"observed"`
    Owned bool `json:"owned"`
}

type ReconcileRequest struct {
    NodeID string `json:"node_id"`
    ExpectedObservedRevision uint64 `json:"expected_observed_revision"`
    Actor string `json:"actor"`
    DryRun bool `json:"dry_run"`
}

type ReconcileResult struct {
    NodeID string `json:"node_id"`
    Drift []DriftItem `json:"drift"`
    Applied bool `json:"applied"`
    TransactionID string `json:"transaction_id"`
}

type RolloutRequest struct {
    Revision uint64 `json:"revision"`
    Selector map[string]string `json:"selector"`
    WaveSize int `json:"wave_size"`
    CanaryNodes []string `json:"canary_nodes"`
    Actor string `json:"actor"`
}

type RolloutNode struct {
    NodeID string `json:"node_id"`
    Revision uint64 `json:"revision"`
    Status string `json:"status"`
    Error string `json:"error"`
}

type RolloutWave struct {
    Index int `json:"index"`
    Nodes []RolloutNode `json:"nodes"`
    Status string `json:"status"`
}

type Rollout struct {
    ID string `json:"id"`
    Revision uint64 `json:"revision"`
    Selector map[string]string `json:"selector"`
    Actor string `json:"actor"`
    Waves []RolloutWave `json:"waves"`
    Status string `json:"status"`
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
}

type AuditEvent struct {
    Sequence uint64 `json:"sequence"`
    Time time.Time `json:"time"`
    Actor string `json:"actor"`
    Action string `json:"action"`
    ObjectType string `json:"object_type"`
    ObjectID string `json:"object_id"`
    Revision uint64 `json:"revision"`
    Detail map[string]any `json:"detail"`
}

func canonicalPrefix(value string) (string, error) {
    value = strings.TrimSpace(value)
    if value == "" || value == "default" {
        return "0.0.0.0/0", nil
    }
    prefix, err := netip.ParsePrefix(value)
    if err != nil {
        return "", fmt.Errorf("parse prefix %q: %w", value, err)
    }
    return prefix.Masked().String(), nil
}

func canonicalAddress(value string) (string, error) {
    value = strings.TrimSpace(value)
    if value == "" {
        return "", nil
    }
    addr, err := netip.ParseAddr(value)
    if err != nil {
        return "", fmt.Errorf("parse address %q: %w", value, err)
    }
    return addr.Unmap().String(), nil
}

func normalizeRoute(route Route) (Route, error) {
    destination, err := canonicalPrefix(route.Destination)
    if err != nil {
        return Route{}, err
    }
    route.Destination = destination
    route.Family = familyForPrefix(destination)
    route.Protocol = strings.ToLower(strings.TrimSpace(route.Protocol))
    route.Scope = strings.ToLower(strings.TrimSpace(route.Scope))
    route.Type = strings.ToLower(strings.TrimSpace(route.Type))
    route.Owner = strings.TrimSpace(route.Owner)
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
    return route, nil
}

func normalizeRule(rule PolicyRule) (PolicyRule, error) {
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
    rule.Owner = strings.TrimSpace(rule.Owner)
    return rule, nil
}

func familyForPrefix(value string) string {
    prefix, err := netip.ParsePrefix(value)
    if err != nil {
        return "unknown"
    }
    if prefix.Addr().Is6() {
        return "ipv6"
    }
    return "ipv4"
}

func routeIdentity(route Route) string {
    parts := []string{
        route.NodeID,
        route.Family,
        route.Destination,
        strconvI(route.Table),
        strconvI(route.Metric),
        route.Type,
    }
    for _, hop := range route.NextHops {
        parts = append(parts, hop.Gateway, hop.Interface, strconvI(hop.Weight))
    }
    return strings.Join(parts, "|")
}

func ruleIdentity(rule PolicyRule) string {
    return strings.Join([]string{
        rule.NodeID,
        rule.Family,
        strconvI(rule.Priority),
        rule.Source,
        rule.Destination,
        strconvI(rule.Mark),
        strconvI(rule.Mask),
        rule.InputInterface,
        rule.OutputInterface,
        strconvI(rule.Table),
        rule.Action,
    }, "|")
}

func stableNextHops(hops []NextHop) []NextHop {
    out := append([]NextHop(nil), hops...)
    sort.Slice(out, func(i, j int) bool {
        if out[i].Gateway != out[j].Gateway {
            return out[i].Gateway < out[j].Gateway
        }
        if out[i].Interface != out[j].Interface {
            return out[i].Interface < out[j].Interface
        }
        return out[i].Weight < out[j].Weight
    })
    return out
}

func strconvI(value int) string {
    return fmt.Sprintf("%d", value)
}
