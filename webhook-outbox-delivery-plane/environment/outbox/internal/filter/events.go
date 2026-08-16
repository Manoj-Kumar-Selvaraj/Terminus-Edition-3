package filter

import (
	"net/url"
	"strconv"
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

// ParseQuery maps common list-events query parameters onto an EventQuery.
func ParseQuery(values url.Values) EventQuery {
	q := EventQuery{
		Status:   strings.TrimSpace(values.Get("status")),
		Endpoint: strings.TrimSpace(values.Get("endpoint")),
	}
	if lim, err := strconv.Atoi(values.Get("limit")); err == nil {
		q.Limit = lim
	}
	if v := values.Get("has_lease"); v != "" {
		b := v == "1" || strings.EqualFold(v, "true") || strings.EqualFold(v, "yes")
		q.HasLease = &b
	}
	if sec, err := strconv.Atoi(values.Get("min_age_sec")); err == nil && sec > 0 {
		q.MinAge = time.Duration(sec) * time.Second
	}
	if sec, err := strconv.Atoi(values.Get("max_age_sec")); err == nil && sec > 0 {
		q.MaxAge = time.Duration(sec) * time.Second
	}
	return q
}

// CountByStatus tallies events that survive the query without applying Limit.
func CountByStatus(list []model.Event, q EventQuery, now time.Time) map[string]int {
	out := map[string]int{}
	q2 := q
	q2.Limit = 0
	for _, ev := range list {
		if Match(ev, q2, now) {
			out[ev.Status]++
		}
	}
	return out
}

// WithLeaseOnly returns events that currently advertise a lease owner.
func WithLeaseOnly(list []model.Event) []model.Event {
	yes := true
	return Apply(list, EventQuery{HasLease: &yes}, time.Now().UTC())
}
