// Package store keeps the live edge control-plane records in memory and
// mirrors every mutation onto a JSON state file so a restart resumes cleanly.
package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
)

const (
	stateFileName = "state.json"
	maxErrorRate  = 2.0
)

// Store is the concurrency-safe edge control-plane record set.
type Store struct {
	mu sync.Mutex

	dir string

	networks map[string]Network
	pools    map[string]Pool
	canaries map[string]Canary
	wafs     map[string]WAF
	tls      map[string]TLSCert
	dns      map[string]DNSRecord

	requests int64
	errors   int64

	// Sliding window of recent outcomes (true = error) for error_rate_pct.
	window     []bool
	windowSize int
	windowPos  int
	windowFill int
}

type persisted struct {
	Networks map[string]Network   `json:"networks"`
	Pools    map[string]Pool      `json:"pools"`
	Canaries map[string]Canary    `json:"canaries"`
	WAFs     map[string]WAF       `json:"wafs"`
	TLS      map[string]TLSCert   `json:"tls"`
	DNS      map[string]DNSRecord `json:"dns"`
	Requests int64                `json:"requests"`
	Errors   int64                `json:"errors"`
	Window   []bool               `json:"window,omitempty"`
}

// Open prepares the state directory and reloads anything already persisted.
func Open(dir string, windowSize int) (*Store, error) {
	if windowSize <= 0 {
		windowSize = 200
	}
	if err := os.MkdirAll(dir, 0o775); err != nil {
		return nil, err
	}
	s := &Store{
		dir:        dir,
		networks:   map[string]Network{},
		pools:      map[string]Pool{},
		canaries:   map[string]Canary{},
		wafs:       map[string]WAF{},
		tls:        map[string]TLSCert{},
		dns:        map[string]DNSRecord{},
		window:     make([]bool, windowSize),
		windowSize: windowSize,
	}
	if err := s.load(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Store) statePath() string {
	return filepath.Join(s.dir, stateFileName)
}

func (s *Store) load() error {
	path := s.statePath()
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	if len(raw) == 0 {
		return nil
	}
	var p persisted
	if err := json.Unmarshal(raw, &p); err != nil {
		return fmt.Errorf("state file %s: %w", path, err)
	}
	if p.Networks != nil {
		s.networks = p.Networks
	}
	if p.Pools != nil {
		s.pools = p.Pools
	}
	if p.Canaries != nil {
		s.canaries = p.Canaries
	}
	if p.WAFs != nil {
		s.wafs = p.WAFs
	}
	if p.TLS != nil {
		s.tls = p.TLS
	}
	if p.DNS != nil {
		s.dns = p.DNS
	}
	s.requests = p.Requests
	s.errors = p.Errors
	if len(p.Window) > 0 {
		// Rebuild sliding window from persisted outcomes, truncated to size.
		for _, outcome := range p.Window {
			s.recordWindowLocked(outcome)
		}
	}
	return nil
}

func (s *Store) persistLocked() error {
	p := persisted{
		Networks: s.networks,
		Pools:    s.pools,
		Canaries: s.canaries,
		WAFs:     s.wafs,
		TLS:      s.tls,
		DNS:      s.dns,
		Requests: s.requests,
		Errors:   s.errors,
	}
	if s.windowFill > 0 {
		n := s.windowFill
		if n > s.windowSize {
			n = s.windowSize
		}
		p.Window = make([]bool, n)
		start := 0
		if s.windowFill >= s.windowSize {
			start = s.windowPos
		}
		for i := 0; i < n; i++ {
			p.Window[i] = s.window[(start+i)%s.windowSize]
		}
	}
	raw, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	tmp := s.statePath() + ".tmp"
	if err := os.WriteFile(tmp, append(raw, '\n'), 0o664); err != nil {
		return err
	}
	return os.Rename(tmp, s.statePath())
}

func dnsKey(zone, name string) string {
	return zone + "/" + name
}

// Snapshot returns a deep-ish copy of the full state suitable for JSON.
func (s *Store) Snapshot() Snapshot {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.snapshotLocked()
}

func (s *Store) snapshotLocked() Snapshot {
	out := Snapshot{
		Networks: map[string]Network{},
		Pools:    map[string]Pool{},
		Canaries: map[string]Canary{},
		WAFs:     map[string]WAF{},
		TLS:      map[string]TLSCert{},
		DNS:      map[string]DNSRecord{},
		Metrics:  s.metricsLocked(),
	}
	for k, v := range s.networks {
		out.Networks[k] = v
	}
	for k, v := range s.pools {
		cp := v
		cp.Origins = append([]Origin(nil), v.Origins...)
		out.Pools[k] = cp
	}
	for k, v := range s.canaries {
		out.Canaries[k] = v
	}
	for k, v := range s.wafs {
		cp := v
		cp.Rules = append([]WAFRule(nil), v.Rules...)
		out.WAFs[k] = cp
	}
	for k, v := range s.tls {
		out.TLS[k] = v
	}
	for k, v := range s.dns {
		out.DNS[k] = v
	}
	return out
}

// Metrics returns the live counters.
func (s *Store) Metrics() Metrics {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.metricsLocked()
}

func (s *Store) metricsLocked() Metrics {
	return Metrics{
		Requests:          s.requests,
		Errors:            s.errors,
		ErrorRatePct:      s.errorRateLocked(),
		CanaryWeightGreen: s.primaryCanaryWeightLocked(),
		DNSTargetPool:     s.primaryDNSTargetLocked(),
	}
}

func (s *Store) errorRateLocked() float64 {
	if s.windowFill == 0 {
		return 0
	}
	n := s.windowFill
	if n > s.windowSize {
		n = s.windowSize
	}
	var errs int
	start := 0
	if s.windowFill >= s.windowSize {
		start = s.windowPos
	}
	for i := 0; i < n; i++ {
		if s.window[(start+i)%s.windowSize] {
			errs++
		}
	}
	return (float64(errs) / float64(n)) * 100.0
}

func (s *Store) primaryCanaryWeightLocked() int {
	if len(s.canaries) == 0 {
		return 0
	}
	ids := make([]string, 0, len(s.canaries))
	for id := range s.canaries {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return s.canaries[ids[0]].WeightGreen
}

func (s *Store) primaryDNSTargetLocked() string {
	if len(s.dns) == 0 {
		return ""
	}
	keys := make([]string, 0, len(s.dns))
	for k := range s.dns {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return s.dns[keys[0]].TargetPool
}

func (s *Store) primaryCanaryLocked() (Canary, bool) {
	if len(s.canaries) == 0 {
		return Canary{}, false
	}
	ids := make([]string, 0, len(s.canaries))
	for id := range s.canaries {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return s.canaries[ids[0]], true
}

// PutNetwork upserts a network fabric record.
func (s *Store) PutNetwork(n Network) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(n.ID) == "" {
		return &ValidationError{Msg: "network id is required"}
	}
	if strings.TrimSpace(n.CIDR) == "" {
		return &ValidationError{Msg: "network cidr is required"}
	}
	if strings.TrimSpace(n.Region) == "" {
		return &ValidationError{Msg: "network region is required"}
	}
	switch n.Status {
	case "ready", "pending", "failed", "draining":
	default:
		return &ValidationError{Msg: "network status must be ready|pending|failed|draining"}
	}

	// Demoting a network away from ready is blocked while pools still attach.
	if existing, ok := s.networks[n.ID]; ok && existing.Status == "ready" && n.Status != "ready" {
		for _, p := range s.pools {
			if p.NetworkID == n.ID {
				return &ConflictError{Msg: fmt.Sprintf("network %s still has attached pools; cannot leave ready", n.ID)}
			}
		}
	}

	s.networks[n.ID] = n
	return s.persistLocked()
}

// PutPool upserts an origin pool. The parent network must already be ready.
func (s *Store) PutPool(p Pool) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(p.ID) == "" {
		return &ValidationError{Msg: "pool id is required"}
	}
	if strings.TrimSpace(p.NetworkID) == "" {
		return &ValidationError{Msg: "pool network_id is required"}
	}
	switch p.Color {
	case "blue", "green":
	default:
		return &ValidationError{Msg: "pool color must be blue|green"}
	}
	if p.MinHealthy < 0 {
		return &ValidationError{Msg: "pool min_healthy must be >= 0"}
	}
	if p.Origins == nil {
		p.Origins = []Origin{}
	}
	for i, o := range p.Origins {
		if strings.TrimSpace(o.ID) == "" {
			return &ValidationError{Msg: fmt.Sprintf("origins[%d].id is required", i)}
		}
		if strings.TrimSpace(o.Host) == "" {
			return &ValidationError{Msg: fmt.Sprintf("origins[%d].host is required", i)}
		}
		if o.Port <= 0 || o.Port > 65535 {
			return &ValidationError{Msg: fmt.Sprintf("origins[%d].port is invalid", i)}
		}
	}

	net, ok := s.networks[p.NetworkID]
	if !ok {
		return &ConflictError{Msg: fmt.Sprintf("network %s not found", p.NetworkID)}
	}
	if net.Status != "ready" {
		return &ConflictError{Msg: fmt.Sprintf("network %s status is %q; dependents require ready", p.NetworkID, net.Status)}
	}

	// If this pool is already referenced by a live canary with weight > 0,
	// refuse updates that would drop below min_healthy.
	if err := s.validatePoolHealthyForCanariesLocked(p); err != nil {
		return err
	}

	s.pools[p.ID] = p
	return s.persistLocked()
}

func (s *Store) validatePoolHealthyForCanariesLocked(p Pool) error {
	for _, c := range s.canaries {
		if c.WeightGreen <= 0 {
			continue
		}
		if c.BluePool != p.ID && c.GreenPool != p.ID {
			continue
		}
		if !poolMeetsMinHealthy(p) {
			return &ConflictError{Msg: fmt.Sprintf("pool %s would drop below min_healthy while canary weight_green>0", p.ID)}
		}
	}
	return nil
}

func poolMeetsMinHealthy(p Pool) bool {
	return HealthyOriginCount(p) >= EffectiveMinHealthy(p)
}

func (s *Store) poolHealthyLocked(id string) bool {
	p, ok := s.pools[id]
	if !ok {
		return false
	}
	return poolMeetsMinHealthy(p)
}

// PutCanary upserts a canary route with fail-closed weight guards.
func (s *Store) PutCanary(c Canary) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(c.ID) == "" {
		return &ValidationError{Msg: "canary id is required"}
	}
	if strings.TrimSpace(c.BluePool) == "" || strings.TrimSpace(c.GreenPool) == "" {
		return &ValidationError{Msg: "canary blue_pool and green_pool are required"}
	}
	if c.WeightGreen < 0 || c.WeightGreen > 100 {
		return &ValidationError{Msg: "weight_green must be between 0 and 100"}
	}

	blue, ok := s.pools[c.BluePool]
	if !ok {
		return &ConflictError{Msg: fmt.Sprintf("blue_pool %s not found", c.BluePool)}
	}
	green, ok := s.pools[c.GreenPool]
	if !ok {
		return &ConflictError{Msg: fmt.Sprintf("green_pool %s not found", c.GreenPool)}
	}
	if blue.Color != "blue" {
		return &ConflictError{Msg: fmt.Sprintf("pool %s color is %q; expected blue", c.BluePool, blue.Color)}
	}
	if green.Color != "green" {
		return &ConflictError{Msg: fmt.Sprintf("pool %s color is %q; expected green", c.GreenPool, green.Color)}
	}

	prevWeight := 0
	if existing, ok := s.canaries[c.ID]; ok {
		prevWeight = existing.WeightGreen
	}

	if c.WeightGreen > 0 {
		if !poolMeetsMinHealthy(blue) {
			return &ConflictError{Msg: fmt.Sprintf("blue_pool %s lacks enough healthy origins for weight_green>0", c.BluePool)}
		}
		if !poolMeetsMinHealthy(green) {
			return &ConflictError{Msg: fmt.Sprintf("green_pool %s lacks enough healthy origins for weight_green>0", c.GreenPool)}
		}
	}

	// Reject weight increases while the recent error rate is elevated,
	// unless the caller is rolling all the way back to zero.
	if c.WeightGreen > prevWeight && c.WeightGreen != 0 {
		rate := s.errorRateLocked()
		if rate > maxErrorRate {
			return &ConflictError{Msg: fmt.Sprintf("error_rate_pct %.2f exceeds %.1f; cannot increase weight_green", rate, maxErrorRate)}
		}
	}

	s.canaries[c.ID] = c
	return s.persistLocked()
}

// PutWAF upserts a WAF policy.
func (s *Store) PutWAF(w WAF) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(w.ID) == "" {
		return &ValidationError{Msg: "waf id is required"}
	}
	switch w.Mode {
	case "enforce", "detect":
	default:
		return &ValidationError{Msg: "waf mode must be enforce|detect"}
	}
	if w.Rules == nil {
		w.Rules = []WAFRule{}
	}
	for i, r := range w.Rules {
		if strings.TrimSpace(r.ID) == "" {
			return &ValidationError{Msg: fmt.Sprintf("rules[%d].id is required", i)}
		}
		switch r.Action {
		case "block", "allow":
		default:
			return &ValidationError{Msg: fmt.Sprintf("rules[%d].action must be block|allow", i)}
		}
		if strings.TrimSpace(r.Match) == "" {
			return &ValidationError{Msg: fmt.Sprintf("rules[%d].match is required", i)}
		}
	}

	// Leaving enforce while DNS still requires it is fail-closed.
	if existing, ok := s.wafs[w.ID]; ok && existing.Mode == "enforce" && w.Mode != "enforce" {
		for _, d := range s.dns {
			if d.RequireWAFEnforce {
				return &ConflictError{Msg: fmt.Sprintf("waf %s cannot leave enforce while dns requires it", w.ID)}
			}
		}
	}

	s.wafs[w.ID] = w
	return s.persistLocked()
}

// PutTLS upserts TLS material for a hostname.
func (s *Store) PutTLS(t TLSCert) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(t.ID) == "" {
		return &ValidationError{Msg: "tls id is required"}
	}
	if strings.TrimSpace(t.Hostname) == "" {
		return &ValidationError{Msg: "tls hostname is required"}
	}
	if strings.TrimSpace(t.Fingerprint) == "" {
		return &ValidationError{Msg: "tls fingerprint is required"}
	}

	s.tls[t.ID] = t
	return s.persistLocked()
}

// PutDNS upserts a DNS cutover record with fail-closed cutover guards.
//
// When the body declares require_canary_weight / require_waf_enforce (the
// standard green cutover contract), or the target pool is green, the store
// refuses the write unless:
//   - canary weight_green equals the required weight (typically 100)
//   - at least one WAF policy is in enforce mode
//   - the green pool meets min_healthy
//   - TLS material exists for the derived hostname
func (s *Store) PutDNS(d DNSRecord) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if strings.TrimSpace(d.Zone) == "" || strings.TrimSpace(d.Name) == "" {
		return &ValidationError{Msg: "dns zone and name are required"}
	}
	if strings.TrimSpace(d.TargetPool) == "" {
		return &ValidationError{Msg: "dns target_pool is required"}
	}
	if d.RequireCanaryWeight < 0 || d.RequireCanaryWeight > 100 {
		return &ValidationError{Msg: "require_canary_weight must be between 0 and 100"}
	}

	pool, ok := s.pools[d.TargetPool]
	if !ok {
		return &ConflictError{Msg: fmt.Sprintf("target_pool %s not found", d.TargetPool)}
	}

	cuttingOver := pool.Color == "green" || d.RequireCanaryWeight > 0 || d.RequireWAFEnforce
	if cuttingOver {
		if err := s.validateDNSCutoverLocked(d, pool); err != nil {
			return err
		}
	} else if !poolMeetsMinHealthy(pool) {
		return &ConflictError{Msg: fmt.Sprintf("target_pool %s is unhealthy", d.TargetPool)}
	}

	key := dnsKey(d.Zone, d.Name)
	s.dns[key] = d
	return s.persistLocked()
}

func (s *Store) validateDNSCutoverLocked(d DNSRecord, pool Pool) error {
	reqWeight := d.RequireCanaryWeight
	if reqWeight == 0 {
		// Green cutover without an explicit weight still demands full canary.
		reqWeight = 100
	}

	canary, ok := s.primaryCanaryLocked()
	if !ok {
		return &ConflictError{Msg: "no canary configured; cannot cut over dns"}
	}
	if canary.WeightGreen != reqWeight {
		return &ConflictError{Msg: fmt.Sprintf("canary weight_green is %d; require %d before dns cutover", canary.WeightGreen, reqWeight)}
	}

	if d.RequireWAFEnforce || pool.Color == "green" {
		if !s.anyWAFEnforceLocked() {
			return &ConflictError{Msg: "waf mode enforce required before dns cutover to green"}
		}
	}

	greenID := canary.GreenPool
	if pool.Color == "green" {
		greenID = pool.ID
	}
	if !s.poolHealthyLocked(greenID) {
		return &ConflictError{Msg: fmt.Sprintf("green pool %s is unhealthy", greenID)}
	}

	hostname := dnsHostname(d.Zone, d.Name)
	if !s.hasTLSForHostnameLocked(hostname) {
		return &ConflictError{Msg: fmt.Sprintf("tls missing for hostname %s", hostname)}
	}

	return nil
}

func dnsHostname(zone, name string) string {
	name = strings.TrimSuffix(name, ".")
	zone = strings.TrimSuffix(zone, ".")
	if name == "@" || name == "" {
		return zone
	}
	if strings.HasSuffix(name, "."+zone) {
		return name
	}
	return name + "." + zone
}

func (s *Store) hasTLSForHostnameLocked(hostname string) bool {
	host := strings.ToLower(hostname)
	for _, t := range s.tls {
		if strings.ToLower(t.Hostname) == host {
			return true
		}
	}
	return false
}

func (s *Store) anyWAFEnforceLocked() bool {
	for _, w := range s.wafs {
		if w.Mode == "enforce" {
			return true
		}
	}
	return false
}

// ResetTraffic clears request/error counters and the sliding window.
func (s *Store) ResetTraffic() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.requests = 0
	s.errors = 0
	s.window = make([]bool, s.windowSize)
	s.windowPos = 0
	s.windowFill = 0
	return s.persistLocked()
}

// RecordRequest records one synthetic traffic outcome. isError true counts
// toward both the absolute error counter and the recent error-rate window.
func (s *Store) RecordRequest(isError bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.requests++
	if isError {
		s.errors++
	}
	s.recordWindowLocked(isError)
	// Persist periodically via traffic package; hot path stays in-memory.
}

func (s *Store) recordWindowLocked(isError bool) {
	s.window[s.windowPos] = isError
	s.windowPos = (s.windowPos + 1) % s.windowSize
	if s.windowFill < s.windowSize {
		s.windowFill++
	}
}

// PersistNow flushes the in-memory counters to disk.
func (s *Store) PersistNow() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.persistLocked()
}

// RoutingView is a read-only snapshot the traffic simulator uses each tick.
type RoutingView struct {
	WeightGreen   int
	BluePool      *Pool
	GreenPool     *Pool
	DNSTargetPool *Pool
	WAFEnforce    bool
}

// RoutingSnapshot returns the current routing inputs for the simulator.
func (s *Store) RoutingSnapshot() RoutingView {
	s.mu.Lock()
	defer s.mu.Unlock()

	view := RoutingView{}
	if c, ok := s.primaryCanaryLocked(); ok {
		view.WeightGreen = c.WeightGreen
		if p, ok := s.pools[c.BluePool]; ok {
			cp := p
			cp.Origins = append([]Origin(nil), p.Origins...)
			view.BluePool = &cp
		}
		if p, ok := s.pools[c.GreenPool]; ok {
			cp := p
			cp.Origins = append([]Origin(nil), p.Origins...)
			view.GreenPool = &cp
		}
	}
	if target := s.primaryDNSTargetLocked(); target != "" {
		if p, ok := s.pools[target]; ok {
			cp := p
			cp.Origins = append([]Origin(nil), p.Origins...)
			view.DNSTargetPool = &cp
		}
	}
	view.WAFEnforce = s.anyWAFEnforceLocked()
	return view
}
