package reconcile

import (
	"time"

	"outbox/internal/model"
	"outbox/internal/store"
)

// Sweeper expires stale leases so pending work becomes claimable again.
type Sweeper struct {
	Store *store.Store
}

type SweepResult struct {
	ExpiredLeases int
	CheckedAt     time.Time
}

func (s *Sweeper) ExpireStaleLeases(now time.Time) (SweepResult, error) {
	res := SweepResult{CheckedAt: now.UTC()}
	rows, err := s.Store.DB().Query(
		`SELECT id, attempt_count FROM events
		 WHERE status=? AND lease_until IS NOT NULL AND lease_until < ?`,
		model.StatusClaimed, model.FormatTime(now.UTC()),
	)
	if err != nil {
		return res, err
	}
	defer rows.Close()
	type row struct {
		id  string
		att int
	}
	var list []row
	for rows.Next() {
		var r row
		if err := rows.Scan(&r.id, &r.att); err != nil {
			return res, err
		}
		list = append(list, r)
	}
	for _, r := range list {
		if err := s.Store.ClearEventLease(r.id, model.StatusPending, now.UTC(), r.att); err != nil {
			return res, err
		}
		res.ExpiredLeases++
	}
	return res, nil
}

func (s *Sweeper) CountStale(now time.Time) (int, error) {
	var n int
	err := s.Store.DB().QueryRow(
		`SELECT COUNT(*) FROM events WHERE status=? AND lease_until IS NOT NULL AND lease_until < ?`,
		model.StatusClaimed, model.FormatTime(now.UTC()),
	).Scan(&n)
	return n, err
}
