package reconcile

import (
	"database/sql"
	"time"

	"outbox/internal/lease"
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
	SkippedFresh  int
}

func (s *Sweeper) ExpireStaleLeases(now time.Time) (SweepResult, error) {
	res := SweepResult{CheckedAt: now.UTC()}
	rows, err := s.Store.DB().Query(
		`SELECT id, attempt_count, lease_owner, lease_until FROM events
		 WHERE status=? AND lease_until IS NOT NULL AND lease_until < ?`,
		model.StatusClaimed, model.FormatTime(now.UTC()),
	)
	if err != nil {
		return res, err
	}
	defer rows.Close()
	type row struct {
		id    string
		att   int
		owner *string
		until *time.Time
	}
	var list []row
	for rows.Next() {
		var r row
		var ownerNS sql.NullString
		var untilNS sql.NullString
		if err := rows.Scan(&r.id, &r.att, &ownerNS, &untilNS); err != nil {
			return res, err
		}
		if ownerNS.Valid {
			v := ownerNS.String
			r.owner = &v
		}
		if untilNS.Valid {
			t, perr := model.ParseTime(untilNS.String)
			if perr == nil {
				r.until = &t
			}
		}
		list = append(list, r)
	}
	for _, r := range list {
		if !lease.StaleClaimed(model.StatusClaimed, r.owner, r.until, now) {
			res.SkippedFresh++
			continue
		}
		if !lease.Expired(r.until, now) {
			res.SkippedFresh++
			continue
		}
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

// PreviewStale returns ids that would expire under lease wall-clock rules.
func (s *Sweeper) PreviewStale(now time.Time, limit int) ([]string, error) {
	if limit < 1 {
		limit = 50
	}
	rows, err := s.Store.DB().Query(
		`SELECT id, lease_owner, lease_until FROM events WHERE status=? LIMIT ?`,
		model.StatusClaimed, limit*4,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var id string
		var ownerNS sql.NullString
		var untilNS sql.NullString
		if err := rows.Scan(&id, &ownerNS, &untilNS); err != nil {
			return nil, err
		}
		var owner *string
		var until *time.Time
		if ownerNS.Valid {
			v := ownerNS.String
			owner = &v
		}
		if untilNS.Valid {
			t, perr := model.ParseTime(untilNS.String)
			if perr == nil {
				until = &t
			}
		}
		if lease.StaleClaimed(model.StatusClaimed, owner, until, now) {
			out = append(out, id)
			if len(out) >= limit {
				break
			}
		}
	}
	return out, rows.Err()
}
