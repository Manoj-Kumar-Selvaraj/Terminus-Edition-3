package drain

import (
	"context"
	"sort"
	"sync"
	"time"

	rt "edge-router/internal/runtime"
)

type State struct {
	PoolID string `json:"pool_id"`
	Identity string `json:"identity"`
	Incarnation uint64 `json:"incarnation"`
	Membership rt.MembershipState `json:"membership"`
	Inflight int64 `json:"inflight"`
	Connections int64 `json:"connections"`
	Deadline time.Time `json:"deadline"`
}

type Manager struct {
	registry *rt.Registry
	mu sync.Mutex
	draining map[string]*rt.EndpointRuntime
	retired []State
	maxRetired int
}

func New(registry *rt.Registry) *Manager {
	return &Manager{registry: registry, draining: make(map[string]*rt.EndpointRuntime), maxRetired: 256}
}

func key(endpoint *rt.EndpointRuntime) string {
	return endpoint.PoolID + "\x00" + endpoint.Identity
}

func (m *Manager) Begin(endpoint *rt.EndpointRuntime, timeout time.Duration) {
	if endpoint == nil {
		return
	}
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	endpoint.MarkDraining(time.Now().UTC().Add(timeout))
	m.mu.Lock()
	m.draining[key(endpoint)] = endpoint
	m.mu.Unlock()
}

func (m *Manager) Run(ctx context.Context) error {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case now := <-ticker.C:
			m.Sweep(now.UTC())
		}
	}
}

func (m *Manager) Sweep(now time.Time) int {
	m.mu.Lock()
	defer m.mu.Unlock()
	retired := 0
	for id, endpoint := range m.draining {
		inflight, connections := endpoint.Counts()
		deadline := endpoint.Deadline()
		if inflight > 0 {
			continue
		}
		if connections > 0 && (deadline.IsZero() || now.Before(deadline)) {
			continue
		}
		endpoint.Retire()
		delete(m.draining, id)
		m.retired = append(m.retired, State{
			PoolID: endpoint.PoolID,
			Identity: endpoint.Identity,
			Incarnation: endpoint.Incarnation,
			Membership: endpoint.Membership(),
			Inflight: inflight,
			Connections: connections,
			Deadline: deadline,
		})
		retired++
	}
	if len(m.retired) > m.maxRetired {
		m.retired = append([]State(nil), m.retired[len(m.retired)-m.maxRetired:]...)
	}
	return retired
}

func (m *Manager) Draining() []State {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]State, 0, len(m.draining))
	for _, endpoint := range m.draining {
		inflight, connections := endpoint.Counts()
		out = append(out, State{
			PoolID: endpoint.PoolID,
			Identity: endpoint.Identity,
			Incarnation: endpoint.Incarnation,
			Membership: endpoint.Membership(),
			Inflight: inflight,
			Connections: connections,
			Deadline: endpoint.Deadline(),
		})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].PoolID != out[j].PoolID {
			return out[i].PoolID < out[j].PoolID
		}
		return out[i].Identity < out[j].Identity
	})
	return out
}

func (m *Manager) Retired(limit int) []State {
	m.mu.Lock()
	defer m.mu.Unlock()
	if limit <= 0 || limit > len(m.retired) {
		limit = len(m.retired)
	}
	return append([]State(nil), m.retired[len(m.retired)-limit:]...)
}

func (m *Manager) ForceRetireAll() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	count := 0
	for id, endpoint := range m.draining {
		endpoint.Retire()
		delete(m.draining, id)
		count++
	}
	return count
}
