package metrics

import (
	"sync"
	"time"
)

type Snapshot struct {
	mu        sync.Mutex
	Enqueued  int64
	Claimed   int64
	Delivered int64
	Failed    int64
	DLQ       int64
	Replayed  int64
	QuotaHits int64
	Lease409  int64
	Started   time.Time
}

func New() *Snapshot {
	return &Snapshot{Started: time.Now().UTC()}
}

func (s *Snapshot) Inc(field *int64) {
	if s == nil {
		return
	}
	s.mu.Lock()
	*field++
	s.mu.Unlock()
}

func (s *Snapshot) Add(field *int64, n int64) {
	if s == nil || n == 0 {
		return
	}
	s.mu.Lock()
	*field += n
	s.mu.Unlock()
}

func (s *Snapshot) View() map[string]any {
	if s == nil {
		return map[string]any{}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]any{
		"enqueued":   s.Enqueued,
		"claimed":    s.Claimed,
		"delivered":  s.Delivered,
		"failed":     s.Failed,
		"dlq":        s.DLQ,
		"replayed":   s.Replayed,
		"quota_hits": s.QuotaHits,
		"lease_409":  s.Lease409,
		"uptime_sec": int(time.Since(s.Started).Seconds()),
	}
}

func (s *Snapshot) Totals() (enqueued, claimed, delivered, failed, dlq int64) {
	if s == nil {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.Enqueued, s.Claimed, s.Delivered, s.Failed, s.DLQ
}
