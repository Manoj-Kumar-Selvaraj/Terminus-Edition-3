package runtime

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type MembershipState string
type HealthState string
type SnapshotState string

type SelectionPolicy struct {
	Mode string `json:"mode"`
	StickyHeader string `json:"sticky_header,omitempty"`
	AffinityTTLSeconds int `json:"affinity_ttl_seconds,omitempty"`
	AffinityCapacity int `json:"affinity_capacity,omitempty"`
}

type RetryPolicy struct {
	MaxAttempts int `json:"max_attempts"`
	RetryStatus []int `json:"retry_status,omitempty"`
}

type HealthPolicy struct {
	Path string `json:"path,omitempty"`
	IntervalMillis int `json:"interval_millis,omitempty"`
	TimeoutMillis int `json:"timeout_millis,omitempty"`
	HealthyThreshold int `json:"healthy_threshold,omitempty"`
	UnhealthyThreshold int `json:"unhealthy_threshold,omitempty"`
}

type DrainPolicy struct {
	TimeoutMillis int `json:"timeout_millis"`
}

type EndpointSpec struct {
	Address string `json:"address"`
	Weight int `json:"weight"`
	Transport string `json:"transport,omitempty"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type PoolSpec struct {
	ID string `json:"id"`
	Endpoints []EndpointSpec `json:"endpoints"`
	Selection SelectionPolicy `json:"selection"`
	Retry RetryPolicy `json:"retry"`
	Failover []string `json:"failover,omitempty"`
	Health HealthPolicy `json:"health"`
	Drain DrainPolicy `json:"drain"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type MatchSpec struct {
	Host string `json:"host,omitempty"`
	PathPrefix string `json:"path_prefix,omitempty"`
	Methods []string `json:"methods,omitempty"`
}

type RouteSpec struct {
	ID string `json:"id"`
	Match MatchSpec `json:"match"`
	PoolID string `json:"pool_id"`
	Priority int `json:"priority,omitempty"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type SourceSnapshot struct {
	Source string `json:"source"`
	Revision int64 `json:"revision"`
	Routes []RouteSpec `json:"routes,omitempty"`
	Pools []PoolSpec `json:"pools,omitempty"`
	ObservedAt string `json:"observed_at,omitempty"`
}

type DesiredState struct {
	SchemaVersion int `json:"schema_version"`
	Routes []RouteSpec `json:"routes"`
	Pools []PoolSpec `json:"pools"`
	SourceRevisions map[string]int64 `json:"source_revisions"`
	SourceDigests map[string]string `json:"source_digests"`
}

type CompiledRoute struct {
	ID string `json:"id"`
	Host string `json:"host,omitempty"`
	PathPrefix string `json:"path_prefix,omitempty"`
	Methods map[string]struct{} `json:"-"`
	PoolID string `json:"pool_id"`
	Priority int `json:"priority"`
	SemanticDigest string `json:"semantic_digest"`
}

type EndpointView struct {
	Identity string `json:"identity"`
	Address string `json:"address"`
	Weight int `json:"weight"`
	Incarnation uint64 `json:"incarnation"`
	Runtime *EndpointRuntime `json:"-"`
}

type PoolView struct {
	ID string `json:"id"`
	Endpoints []EndpointView `json:"endpoints"`
	Selection SelectionPolicy `json:"selection"`
	Retry RetryPolicy `json:"retry"`
	Failover []string `json:"failover,omitempty"`
	Health HealthPolicy `json:"health"`
	Drain DrainPolicy `json:"drain"`
	Compatibility string `json:"compatibility"`
}

type RuntimeSnapshot struct {
	Generation uint64 `json:"generation"`
	Routes []CompiledRoute `json:"routes"`
	Pools map[string]*PoolView `json:"pools"`
	Desired DesiredState `json:"desired"`
	SourceRevisions map[string]int64 `json:"source_revisions"`
	SourceDigests map[string]string `json:"source_digests"`
	PublishedAt time.Time `json:"published_at"`
	State SnapshotState `json:"state"`
	leaseCount atomic.Int64
}

const (
	MembershipActive MembershipState = "ACTIVE"
	MembershipDraining MembershipState = "DRAINING"
	MembershipRetired MembershipState = "RETIRED"
	HealthUnknown HealthState = "UNKNOWN"
	HealthHealthy HealthState = "HEALTHY"
	HealthUnhealthy HealthState = "UNHEALTHY"
	SnapshotBuilding SnapshotState = "BUILDING"
	SnapshotPublished SnapshotState = "PUBLISHED"
	SnapshotRetired SnapshotState = "RETIRED"
)

type EndpointRuntime struct {
	Identity string
	PoolID string
	Address string
	Incarnation uint64
	mu sync.RWMutex
	membership MembershipState
	health HealthState
	lastHealth time.Time
	inflight int64
	openConnections int64
	drainDeadline time.Time
	closed bool
}

func NewEndpointRuntime(poolID, identity, address string, incarnation uint64) *EndpointRuntime {
	return &EndpointRuntime{
		Identity: identity,
		PoolID: poolID,
		Address: address,
		Incarnation: incarnation,
		membership: MembershipActive,
		health: HealthUnknown,
	}
}

func (e *EndpointRuntime) Membership() MembershipState {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.membership
}

func (e *EndpointRuntime) Health() HealthState {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.health
}

func (e *EndpointRuntime) SetHealth(state HealthState, at time.Time) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.health = state
	e.lastHealth = at
}

func (e *EndpointRuntime) HealthObservation() time.Time {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.lastHealth
}

func (e *EndpointRuntime) MarkDraining(deadline time.Time) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.membership = MembershipDraining
	e.drainDeadline = deadline
}

func (e *EndpointRuntime) Reactivate() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.membership = MembershipActive
	e.closed = false
}

func (e *EndpointRuntime) Retire() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.membership = MembershipRetired
	e.closed = true
}

func (e *EndpointRuntime) BeginRequest() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.closed || e.membership == MembershipRetired {
		return false
	}
	e.inflight++
	return true
}

func (e *EndpointRuntime) EndRequest() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.inflight > 0 {
		e.inflight--
	}
}

func (e *EndpointRuntime) AddConnection() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.closed {
		e.openConnections++
	}
}

func (e *EndpointRuntime) DropConnection() {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.openConnections > 0 {
		e.openConnections--
	}
}

func (e *EndpointRuntime) Counts() (int64, int64) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.inflight, e.openConnections
}

func (e *EndpointRuntime) Deadline() time.Time {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.drainDeadline
}

func (e *EndpointRuntime) Closed() bool {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.closed
}

type AffinityEntry struct {
	RuntimeID string
	EndpointIdentity string
	Incarnation uint64
	ExpiresAt time.Time
	TouchedAt time.Time
}

type PoolRuntime struct {
	ID string
	Compatibility string
	mu sync.Mutex
	cursor uint64
	affinity map[string]AffinityEntry
	selectionCount uint64
}

func NewPoolRuntime(id, compatibility string) *PoolRuntime {
	return &PoolRuntime{ID: id, Compatibility: compatibility, affinity: make(map[string]AffinityEntry)}
}

func (p *PoolRuntime) NextCursor() uint64 {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.cursor++
	p.selectionCount++
	return p.cursor
}

func (p *PoolRuntime) GetAffinity(key string, now time.Time) (AffinityEntry, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	entry, ok := p.affinity[key]
	if !ok {
		return AffinityEntry{}, false
	}
	if !entry.ExpiresAt.IsZero() && now.After(entry.ExpiresAt) {
		delete(p.affinity, key)
		return AffinityEntry{}, false
	}
	entry.TouchedAt = now
	p.affinity[key] = entry
	return entry, true
}

func (p *PoolRuntime) SetAffinity(key string, entry AffinityEntry, capacity int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if capacity <= 0 {
		capacity = 1024
	}
	if len(p.affinity) >= capacity {
		oldestKey := ""
		var oldest time.Time
		for candidate, value := range p.affinity {
			if oldestKey == "" || value.TouchedAt.Before(oldest) {
				oldestKey = candidate
				oldest = value.TouchedAt
			}
		}
		delete(p.affinity, oldestKey)
	}
	p.affinity[key] = entry
}

func (p *PoolRuntime) Prune(now time.Time) int {
	p.mu.Lock()
	defer p.mu.Unlock()
	removed := 0
	for key, entry := range p.affinity {
		if !entry.ExpiresAt.IsZero() && now.After(entry.ExpiresAt) {
			delete(p.affinity, key)
			removed++
		}
	}
	return removed
}

func (p *PoolRuntime) AffinitySize() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return len(p.affinity)
}

type Registry struct {
	mu sync.RWMutex
	pools map[string]*PoolRuntime
	endpoints map[string]*EndpointRuntime
	nextIncarnation uint64
}

func NewRegistry() *Registry {
	return &Registry{
		pools: make(map[string]*PoolRuntime),
		endpoints: make(map[string]*EndpointRuntime),
		nextIncarnation: 1,
	}
}

func endpointRegistryKey(poolID, identity string) string {
	return poolID + "\x00" + identity
}

func (r *Registry) Pool(id, compatibility string) *PoolRuntime {
	r.mu.Lock()
	defer r.mu.Unlock()
	if existing := r.pools[id]; existing != nil && existing.Compatibility == compatibility {
		return existing
	}
	created := NewPoolRuntime(id, compatibility)
	r.pools[id] = created
	return created
}

func (r *Registry) Endpoint(poolID, identity, address string) *EndpointRuntime {
	r.mu.Lock()
	defer r.mu.Unlock()
	key := endpointRegistryKey(poolID, identity)
	if existing := r.endpoints[key]; existing != nil {
		// Intentionally preserves the inherited behavior where a removed identity is
		// toggled active again instead of receiving a distinct membership incarnation.
		existing.Reactivate()
		return existing
	}
	incarnation := r.nextIncarnation
	r.nextIncarnation++
	created := NewEndpointRuntime(poolID, identity, address, incarnation)
	r.endpoints[key] = created
	return created
}

func (r *Registry) LookupEndpoint(poolID, identity string) (*EndpointRuntime, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	ep, ok := r.endpoints[endpointRegistryKey(poolID, identity)]
	return ep, ok
}

func (r *Registry) AllEndpoints() []*EndpointRuntime {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]*EndpointRuntime, 0, len(r.endpoints))
	for _, ep := range r.endpoints {
		out = append(out, ep)
	}
	return out
}

func (r *Registry) PoolCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.pools)
}

func (r *Registry) EndpointCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.endpoints)
}

type Lease struct {
	Snapshot *RuntimeSnapshot
	released atomic.Bool
}

func (s *RuntimeSnapshot) Acquire() *Lease {
	s.leaseCount.Add(1)
	return &Lease{Snapshot: s}
}

func (l *Lease) Release() {
	if l == nil || l.Snapshot == nil || l.released.Swap(true) {
		return
	}
	l.Snapshot.leaseCount.Add(-1)
}

func (s *RuntimeSnapshot) LeaseCount() int64 {
	return s.leaseCount.Load()
}

type PublicationStore struct {
	current atomic.Pointer[RuntimeSnapshot]
	mu sync.Mutex
	routes []CompiledRoute
	pools map[string]*PoolView
	generation uint64
}

func NewPublicationStore() *PublicationStore {
	return &PublicationStore{pools: make(map[string]*PoolView)}
}

func (s *PublicationStore) Current() *RuntimeSnapshot {
	return s.current.Load()
}

func (s *PublicationStore) Acquire() *Lease {
	current := s.current.Load()
	if current == nil {
		return nil
	}
	return current.Acquire()
}

func (s *PublicationStore) Publish(snapshot *RuntimeSnapshot) {
	if snapshot == nil {
		return
	}
	s.mu.Lock()
	// The inherited starter exposes the route and pool pieces independently before
	// the final pointer swap; concurrent readers can therefore observe a mixed view.
	s.routes = snapshot.Routes
	s.mu.Unlock()
	time.Sleep(time.Microsecond)
	s.mu.Lock()
	s.pools = snapshot.Pools
	s.generation = snapshot.Generation
	s.mu.Unlock()
	snapshot.State = SnapshotPublished
	snapshot.PublishedAt = time.Now().UTC()
	previous := s.current.Swap(snapshot)
	if previous != nil {
		previous.State = SnapshotRetired
	}
}

func (s *PublicationStore) PieceView() ([]CompiledRoute, map[string]*PoolView, uint64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	routes := append([]CompiledRoute(nil), s.routes...)
	pools := make(map[string]*PoolView, len(s.pools))
	for id, pool := range s.pools {
		pools[id] = pool
	}
	return routes, pools, s.generation
}

func CanonicalAddress(raw string) (string, error) {
	host, port, err := net.SplitHostPort(strings.TrimSpace(raw))
	if err != nil {
		return "", err
	}
	if parsed := net.ParseIP(strings.Trim(host, "[]")); parsed != nil {
		host = parsed.String()
	} else {
		host = strings.ToLower(strings.TrimSuffix(host, "."))
	}
	return net.JoinHostPort(host, port), nil
}

func SemanticDigest(value any) string {
	payload, _ := json.Marshal(value)
	hash := sha256.Sum256(payload)
	return hex.EncodeToString(hash[:])
}

func StableStringMap(in map[string]string) [][2]string {
	keys := make([]string, 0, len(in))
	for key := range in {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	out := make([][2]string, 0, len(keys))
	for _, key := range keys {
		out = append(out, [2]string{key, in[key]})
	}
	return out
}

func CloneRevisions(in map[string]int64) map[string]int64 {
	out := make(map[string]int64, len(in))
	for key, value := range in {
		out[key] = value
	}
	return out
}

func CloneDigests(in map[string]string) map[string]string {
	out := make(map[string]string, len(in))
	for key, value := range in {
		out[key] = value
	}
	return out
}

func ValidateGeneration(snapshot *RuntimeSnapshot) error {
	if snapshot == nil {
		return fmt.Errorf("nil runtime snapshot")
	}
	if snapshot.Generation == 0 {
		return fmt.Errorf("generation must be positive")
	}
	if len(snapshot.Routes) == 0 {
		return fmt.Errorf("runtime snapshot has no routes")
	}
	if len(snapshot.Pools) == 0 {
		return fmt.Errorf("runtime snapshot has no pools")
	}
	return nil
}
