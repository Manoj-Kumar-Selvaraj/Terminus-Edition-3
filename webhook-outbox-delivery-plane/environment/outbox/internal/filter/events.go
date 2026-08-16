package filter

import (
	"strings"
	"time"

	"outbox/internal/model"
)

type EventQuery struct {
	Status    string
	Endpoint  string
	MinAge    time.Duration
	MaxAge    time.Duration
	HasLease  *bool
	Limit     int
}

func Match(ev model.Event, q EventQuery, now time.Time) bool {
	if q.Status != "" && ev.Status != q.Status {
		return false
	}
	if q.Endpoint != "" && ev.EndpointID != q.Endpoint {
		return false
	}
	age := now.Sub(ev.CreatedAt)
	if q.MinAge > 0 && age < q.MinAge {
		return false
	}
	if q.MaxAge > 0 && age > q.MaxAge {
		return false
	}
	if q.HasLease != nil {
		has := ev.LeaseOwner != nil && strings.TrimSpace(*ev.LeaseOwner) != ""
		if has != *q.HasLease {
			return false
		}
	}
	return true
}

func Apply(list []model.Event, q EventQuery, now time.Time) []model.Event {
	limit := q.Limit
	if limit < 1 {
		limit = len(list)
	}
	var out []model.Event
	for _, ev := range list {
		if Match(ev, q, now) {
			out = append(out, ev)
			if len(out) >= limit {
				break
			}
		}
	}
	return out
}
