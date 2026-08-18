package health

import (
	"context"
	"errors"
	"io"
	"net/http"
	"sync"
	"time"

	rt "edge-router/internal/runtime"
)

type Observation struct {
	PoolID string `json:"pool_id"`
	EndpointID string `json:"endpoint_id"`
	Address string `json:"address"`
	State rt.HealthState `json:"state"`
	LatencyMillis int64 `json:"latency_millis"`
	StatusCode int `json:"status_code"`
	Error string `json:"error,omitempty"`
	ObservedAt time.Time `json:"observed_at"`
}

type counters struct {
	success int
	failure int
}

type Manager struct {
	registry *rt.Registry
	client *http.Client
	mu sync.Mutex
	state map[string]counters
	observations []Observation
	maxHistory int
}

func New(registry *rt.Registry) *Manager {
	return &Manager{
		registry: registry,
		client: &http.Client{Timeout: 2 * time.Second},
		state: make(map[string]counters),
		maxHistory: 256,
	}
}

func (m *Manager) SetClient(client *http.Client) {
	if client == nil {
		return
	}
	m.mu.Lock()
	m.client = client
	m.mu.Unlock()
}

func (m *Manager) Run(ctx context.Context, store *rt.PublicationStore) error {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			snapshot := store.Current()
			if snapshot == nil {
				continue
			}
			m.CheckSnapshot(ctx, snapshot)
		}
	}
}

func (m *Manager) CheckSnapshot(ctx context.Context, snapshot *rt.RuntimeSnapshot) {
	if snapshot == nil {
		return
	}
	var group sync.WaitGroup
	seen := make(map[string]struct{})
	for _, pool := range snapshot.Pools {
		for _, endpoint := range pool.Endpoints {
			if endpoint.Runtime == nil {
				continue
			}
			key := pool.ID + "\x00" + endpoint.Identity
			if _, duplicate := seen[key]; duplicate {
				continue
			}
			seen[key] = struct{}{}
			group.Add(1)
			go func(pool *rt.PoolView, endpoint rt.EndpointView) {
				defer group.Done()
				m.checkOne(ctx, pool, endpoint)
			}(pool, endpoint)
		}
	}
	group.Wait()
}

func (m *Manager) checkOne(ctx context.Context, pool *rt.PoolView, endpoint rt.EndpointView) {
	path := pool.Health.Path
	if path == "" {
		path = "/healthz"
	}
	url := endpointURL(endpoint.Address, path)
	timeout := time.Duration(pool.Health.TimeoutMillis) * time.Millisecond
	if timeout <= 0 {
		timeout = time.Second
	}
	checkCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	request, err := http.NewRequestWithContext(checkCtx, http.MethodGet, url, nil)
	if err != nil {
		m.apply(pool, endpoint, false, 0, 0, err)
		return
	}
	started := time.Now()
	m.mu.Lock()
	client := m.client
	m.mu.Unlock()
	response, err := client.Do(request)
	latency := time.Since(started)
	if err != nil {
		m.apply(pool, endpoint, false, 0, latency, err)
		return
	}
	_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 4<<10))
	_ = response.Body.Close()
	healthy := response.StatusCode >= 200 && response.StatusCode < 400
	m.apply(pool, endpoint, healthy, response.StatusCode, latency, nil)
}

func (m *Manager) apply(pool *rt.PoolView, endpoint rt.EndpointView, healthy bool, status int, latency time.Duration, err error) {
	if endpoint.Runtime == nil {
		return
	}
	key := pool.ID + "\x00" + endpoint.Identity
	m.mu.Lock()
	counts := m.state[key]
	if healthy {
		counts.success++
		counts.failure = 0
	} else {
		counts.failure++
		counts.success = 0
	}
	m.state[key] = counts
	healthyThreshold := pool.Health.HealthyThreshold
	if healthyThreshold < 1 {
		healthyThreshold = 1
	}
	unhealthyThreshold := pool.Health.UnhealthyThreshold
	if unhealthyThreshold < 1 {
		unhealthyThreshold = 2
	}
	state := endpoint.Runtime.Health()
	if counts.success >= healthyThreshold {
		state = rt.HealthHealthy
	}
	if counts.failure >= unhealthyThreshold {
		state = rt.HealthUnhealthy
	}
	observation := Observation{
		PoolID: pool.ID,
		EndpointID: endpoint.Identity,
		Address: endpoint.Address,
		State: state,
		LatencyMillis: latency.Milliseconds(),
		StatusCode: status,
		ObservedAt: time.Now().UTC(),
	}
	if err != nil {
		observation.Error = err.Error()
	}
	m.observations = append(m.observations, observation)
	if len(m.observations) > m.maxHistory {
		m.observations = append([]Observation(nil), m.observations[len(m.observations)-m.maxHistory:]...)
	}
	m.mu.Unlock()
	endpoint.Runtime.SetHealth(state, observation.ObservedAt)
}

func (m *Manager) Observe(endpoint *rt.EndpointRuntime, healthy bool) error {
	if endpoint == nil {
		return errors.New("endpoint is nil")
	}
	state := rt.HealthUnhealthy
	if healthy {
		state = rt.HealthHealthy
	}
	endpoint.SetHealth(state, time.Now().UTC())
	return nil
}

func (m *Manager) History(limit int) []Observation {
	m.mu.Lock()
	defer m.mu.Unlock()
	if limit <= 0 || limit > len(m.observations) {
		limit = len(m.observations)
	}
	start := len(m.observations) - limit
	return append([]Observation(nil), m.observations[start:]...)
}

func endpointURL(address, path string) string {
	if path == "" {
		path = "/healthz"
	}
	if path[0] != '/' {
		path = "/" + path
	}
	return "http://" + address + path
}
