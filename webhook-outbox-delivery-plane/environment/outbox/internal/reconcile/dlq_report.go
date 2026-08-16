package reconcile

import (
	"time"

	"outbox/internal/model"
	"outbox/internal/store"
)

type DLQSummary struct {
	TenantID string `json:"tenant_id"`
	Count    int    `json:"count"`
	Oldest   string `json:"oldest_created_at"`
	Newest   string `json:"newest_created_at"`
}

func DLQByTenant(st *store.Store) ([]DLQSummary, error) {
	rows, err := st.DB().Query(
		`SELECT tenant_id, COUNT(*), MIN(created_at), MAX(created_at)
		 FROM events WHERE status=? GROUP BY tenant_id ORDER BY COUNT(*) DESC`,
		model.StatusDLQ,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []DLQSummary
	for rows.Next() {
		var s DLQSummary
		if err := rows.Scan(&s.TenantID, &s.Count, &s.Oldest, &s.Newest); err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	return out, rows.Err()
}

type AgingBucket struct {
	Label string `json:"label"`
	Count int    `json:"count"`
}

func PendingAging(st *store.Store, now time.Time) ([]AgingBucket, error) {
	thresholds := []struct {
		label string
		age   time.Duration
	}{
		{"lt_1m", time.Minute},
		{"lt_5m", 5 * time.Minute},
		{"lt_30m", 30 * time.Minute},
		{"lt_2h", 2 * time.Hour},
		{"older", 24 * time.Hour},
	}
	var out []AgingBucket
	prev := time.Duration(0)
	for _, th := range thresholds {
		var n int
		var err error
		if th.label == "older" {
			cutoff := now.Add(-th.age)
			err = st.DB().QueryRow(
				`SELECT COUNT(*) FROM events WHERE status=? AND created_at < ?`,
				model.StatusPending, model.FormatTime(cutoff),
			).Scan(&n)
		} else {
			newer := now.Add(-prev)
			older := now.Add(-th.age)
			err = st.DB().QueryRow(
				`SELECT COUNT(*) FROM events WHERE status=? AND created_at <= ? AND created_at > ?`,
				model.StatusPending, model.FormatTime(newer), model.FormatTime(older),
			).Scan(&n)
			prev = th.age
		}
		if err != nil {
			return nil, err
		}
		out = append(out, AgingBucket{Label: th.label, Count: n})
	}
	return out, nil
}
