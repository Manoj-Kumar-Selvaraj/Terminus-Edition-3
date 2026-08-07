// Package traffic runs a background synthetic request loop against the live
// edge routing view (DNS target + canary weights) and feeds counters back
// into the store.
package traffic

import (
	"context"
	"math/rand"
	"sync"
	"time"

	"edgectl/internal/config"
	"edgectl/internal/store"
)

// Simulator continuously emits synthetic requests.
type Simulator struct {
	st  *store.Store
	cfg *config.Config

	mu     sync.Mutex
	cancel context.CancelFunc
	done   chan struct{}

	rng *rand.Rand
}

// New builds a simulator that is idle until Start is called.
func New(st *store.Store, cfg *config.Config) *Simulator {
	return &Simulator{
		st:  st,
		cfg: cfg,
		rng: rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Start begins the background loop. Calling Start again is a no-op while
// a loop is already running.
func (s *Simulator) Start() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cancel != nil {
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	s.cancel = cancel
	s.done = make(chan struct{})
	go s.loop(ctx)
}

// Stop cancels the background loop and waits for it to exit.
func (s *Simulator) Stop() {
	s.mu.Lock()
	cancel := s.cancel
	done := s.done
	s.cancel = nil
	s.done = nil
	s.mu.Unlock()
	if cancel == nil {
		return
	}
	cancel()
	<-done
}

func (s *Simulator) loop(ctx context.Context) {
	defer close(s.done)

	tick := time.Duration(s.cfg.TickMillis) * time.Millisecond
	if tick <= 0 {
		tick = 50 * time.Millisecond
	}
	ticker := time.NewTicker(tick)
	defer ticker.Stop()

	persistEvery := 40
	n := 0

	for {
		select {
		case <-ctx.Done():
			_ = s.st.PersistNow()
			return
		case <-ticker.C:
			s.tick()
			n++
			if n%persistEvery == 0 {
				_ = s.st.PersistNow()
			}
		}
	}
}

func (s *Simulator) tick() {
	view := s.st.RoutingSnapshot()
	pool := s.pickPool(view)
	// Do not poison the error-rate window during cold start before any
	// pool or DNS target exists — canary guards need a clean baseline.
	if pool == nil {
		return
	}
	isError := s.evaluate(pool, view)
	s.st.RecordRequest(isError)
}

func (s *Simulator) pickPool(view store.RoutingView) *store.Pool {
	// Prefer canary split when a canary is configured.
	if view.BluePool != nil || view.GreenPool != nil {
		w := view.WeightGreen
		if w < 0 {
			w = 0
		}
		if w > 100 {
			w = 100
		}
		s.mu.Lock()
		roll := s.rng.Intn(100)
		s.mu.Unlock()
		if roll < w {
			if view.GreenPool != nil {
				return view.GreenPool
			}
		}
		if view.BluePool != nil {
			return view.BluePool
		}
		return view.GreenPool
	}

	// Fall back to the DNS apex target when no canary exists yet.
	return view.DNSTargetPool
}

func (s *Simulator) evaluate(pool *store.Pool, view store.RoutingView) bool {
	healthy := healthyOrigins(*pool)
	need := pool.MinHealthy
	if need < 1 {
		need = 1
	}
	if len(healthy) < need {
		return s.chance(s.cfg.UnhealthyErrorRate)
	}

	// Background noise on healthy origins.
	if s.cfg.BaseErrorRate > 0 && s.chance(s.cfg.BaseErrorRate) {
		return true
	}

	// In enforce mode, a small fraction of synthetic "attacks" are blocked
	// and counted as handled errors so dashboards stay honest.
	if view.WAFEnforce {
		if s.chance(0.005) {
			return true
		}
	}

	return false
}

func healthyOrigins(p store.Pool) []store.Origin {
	out := make([]store.Origin, 0, len(p.Origins))
	for _, o := range p.Origins {
		if o.Healthy {
			out = append(out, o)
		}
	}
	return out
}

func (s *Simulator) chance(p float64) bool {
	if p <= 0 {
		return false
	}
	if p >= 1 {
		return true
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.rng.Float64() < p
}
