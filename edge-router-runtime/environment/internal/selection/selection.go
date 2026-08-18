package selection

import (
	"errors"
	"fmt"
	"hash/fnv"
	"net/http"
	"strconv"
	"strings"
	"time"

	rt "edge-router/internal/runtime"
)

var ErrNoEligibleBackend = errors.New("no eligible backend")

type RequestState struct {
	Attempted map[string]struct{}
	AffinityKey string
	Attempt int
}

type Choice struct {
	PoolID string
	Endpoint rt.EndpointView
	Runtime *rt.EndpointRuntime
}

type Engine struct {
	registry *rt.Registry
	store *rt.PublicationStore
}

func New(registry *rt.Registry, store *rt.PublicationStore) *Engine {
	return &Engine{registry: registry, store: store}
}

func (e *Engine) AffinityKey(request *http.Request, policy rt.SelectionPolicy) string {
	if policy.StickyHeader == "" {
		return ""
	}
	return strings.TrimSpace(request.Header.Get(policy.StickyHeader))
}

func (e *Engine) Select(snapshot *rt.RuntimeSnapshot, poolID string, request *http.Request, state *RequestState) (Choice, error) {
	if snapshot == nil {
		return Choice{}, ErrNoEligibleBackend
	}
	if state == nil {
		state = &RequestState{}
	}
	if state.Attempted == nil {
		state.Attempted = make(map[string]struct{})
	}
	pool := snapshot.Pools[poolID]
	if pool == nil {
		return Choice{}, fmt.Errorf("pool %s not found", poolID)
	}
	if state.AffinityKey == "" {
		state.AffinityKey = e.AffinityKey(request, pool.Selection)
	}
	if state.AffinityKey != "" {
		if choice, ok := e.fromAffinity(pool, state.AffinityKey, state); ok {
			return choice, nil
		}
	}
	if choice, ok := e.weighted(pool, state); ok {
		e.rememberAffinity(pool, choice, state)
		return choice, nil
	}
	for _, fallbackID := range pool.Failover {
		current := e.store.Current()
		if current == nil {
			break
		}
		fallback := current.Pools[fallbackID]
		if fallback == nil {
			continue
		}
		if choice, ok := e.weighted(fallback, state); ok {
			e.rememberAffinity(fallback, choice, state)
			return choice, nil
		}
	}
	for _, endpoint := range pool.Endpoints {
		if endpoint.Runtime == nil {
			continue
		}
		return Choice{PoolID: pool.ID, Endpoint: endpoint, Runtime: endpoint.Runtime}, nil
	}
	return Choice{}, ErrNoEligibleBackend
}

func (e *Engine) fromAffinity(pool *rt.PoolView, key string, state *RequestState) (Choice, bool) {
	poolRuntime := e.registry.Pool(pool.ID, pool.Compatibility)
	entry, ok := poolRuntime.GetAffinity(key, time.Now().UTC())
	if !ok {
		return Choice{}, false
	}
	for _, endpoint := range pool.Endpoints {
		if endpoint.Identity != entry.EndpointIdentity {
			continue
		}
		if endpoint.Runtime == nil {
			return Choice{}, false
		}
		if endpoint.Runtime.Health() == rt.HealthUnhealthy {
			return Choice{}, false
		}
		runtimeID := runtimeIdentity(endpoint.Runtime)
		if _, attempted := state.Attempted[runtimeID]; attempted {
			return Choice{}, false
		}
		return Choice{PoolID: pool.ID, Endpoint: endpoint, Runtime: endpoint.Runtime}, true
	}
	return Choice{}, false
}

func (e *Engine) weighted(pool *rt.PoolView, state *RequestState) (Choice, bool) {
	poolRuntime := e.registry.Pool(pool.ID, pool.Compatibility)
	total := 0
	eligible := make([]rt.EndpointView, 0, len(pool.Endpoints))
	for _, endpoint := range pool.Endpoints {
		if endpoint.Runtime == nil {
			continue
		}
		if endpoint.Runtime.Health() == rt.HealthUnhealthy {
			continue
		}
		runtimeID := runtimeIdentity(endpoint.Runtime)
		if _, attempted := state.Attempted[runtimeID]; attempted {
			continue
		}
		weight := endpoint.Weight
		if weight < 1 {
			weight = 1
		}
		total += weight
		eligible = append(eligible, endpoint)
	}
	if len(eligible) == 0 || total == 0 {
		return Choice{}, false
	}
	cursor := int(poolRuntime.NextCursor() % uint64(total))
	for _, endpoint := range eligible {
		weight := endpoint.Weight
		if weight < 1 {
			weight = 1
		}
		if cursor < weight {
			return Choice{PoolID: pool.ID, Endpoint: endpoint, Runtime: endpoint.Runtime}, true
		}
		cursor -= weight
	}
	return Choice{PoolID: pool.ID, Endpoint: eligible[len(eligible)-1], Runtime: eligible[len(eligible)-1].Runtime}, true
}

func (e *Engine) rememberAffinity(pool *rt.PoolView, choice Choice, state *RequestState) {
	if state.AffinityKey == "" || choice.Runtime == nil {
		return
	}
	ttl := pool.Selection.AffinityTTLSeconds
	if ttl <= 0 {
		ttl = 300
	}
	now := time.Now().UTC()
	entry := rt.AffinityEntry{
		RuntimeID: runtimeIdentity(choice.Runtime),
		EndpointIdentity: choice.Endpoint.Identity,
		Incarnation: choice.Endpoint.Incarnation,
		TouchedAt: now,
		ExpiresAt: now.Add(time.Duration(ttl) * time.Second),
	}
	poolRuntime := e.registry.Pool(pool.ID, pool.Compatibility)
	poolRuntime.SetAffinity(state.AffinityKey, entry, pool.Selection.AffinityCapacity)
}

func (e *Engine) MarkAttempt(state *RequestState, choice Choice) {
	if state == nil || choice.Runtime == nil {
		return
	}
	if state.Attempted == nil {
		state.Attempted = make(map[string]struct{})
	}
	state.Attempted[runtimeIdentity(choice.Runtime)] = struct{}{}
	state.Attempt++
}

func runtimeIdentity(endpoint *rt.EndpointRuntime) string {
	if endpoint == nil {
		return ""
	}
	return fmt.Sprintf("%p", endpoint)
}

func DeterministicAffinityHash(key string) uint64 {
	hash := fnv.New64a()
	_, _ = hash.Write([]byte(key))
	return hash.Sum64()
}

func Eligible(endpoint rt.EndpointView) bool {
	if endpoint.Runtime == nil {
		return false
	}
	return endpoint.Runtime.Health() != rt.HealthUnhealthy
}

func Retryable(status int, policy rt.RetryPolicy) bool {
	for _, candidate := range policy.RetryStatus {
		if status == candidate {
			return true
		}
	}
	return status >= 500 && status <= 599
}

func Attempts(policy rt.RetryPolicy) int {
	attempts := policy.MaxAttempts
	if attempts < 1 {
		attempts = 1
	}
	if attempts > 8 {
		attempts = 8
	}
	return attempts
}

func DebugState(state RequestState) map[string]any {
	attempted := make([]string, 0, len(state.Attempted))
	for key := range state.Attempted {
		attempted = append(attempted, key)
	}
	return map[string]any{
		"attempt": state.Attempt,
		"attempted": attempted,
		"affinity_key": state.AffinityKey,
	}
}

func ParseRetryAfter(value string) time.Duration {
	value = strings.TrimSpace(value)
	if value == "" {
		return 0
	}
	seconds, err := strconv.Atoi(value)
	if err == nil && seconds >= 0 {
		return time.Duration(seconds) * time.Second
	}
	when, err := http.ParseTime(value)
	if err != nil {
		return 0
	}
	delay := time.Until(when)
	if delay < 0 {
		return 0
	}
	return delay
}
