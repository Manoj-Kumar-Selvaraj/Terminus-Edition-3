package report

import (
	"time"

	"outbox/internal/model"
	"outbox/internal/quota"
	"outbox/internal/store"
)

type TenantUsage struct {
	TenantID          string `json:"tenant_id"`
	Slug              string `json:"slug"`
	DeliveriesPerHour int    `json:"deliveries_per_hour"`
	SuccessfulLastHour int   `json:"successful_last_hour"`
	FailedLastHour    int    `json:"failed_last_hour"`
	Pending           int    `json:"pending"`
	DLQ               int    `json:"dlq"`
	QuotaRemaining    int    `json:"quota_remaining"`
}

func TenantUsages(st *store.Store, now time.Time) ([]TenantUsage, error) {
	tenants, err := st.ListTenants()
	if err != nil {
		return nil, err
	}
	since := now.UTC().Add(-quota.Window)
	var out []TenantUsage
	for _, t := range tenants {
		okN, err := st.CountSuccessfulDeliveriesSince(t.ID, since)
		if err != nil {
			return nil, err
		}
		allN, err := st.CountAllAttemptsSince(t.ID, since)
		if err != nil {
			return nil, err
		}
		failN := allN - okN
		if failN < 0 {
			failN = 0
		}
		pending, err := countStatus(st, t.ID, model.StatusPending)
		if err != nil {
			return nil, err
		}
		dlq, err := countStatus(st, t.ID, model.StatusDLQ)
		if err != nil {
			return nil, err
		}
		remain := t.DeliveriesPerHour - okN
		if remain < 0 {
			remain = 0
		}
		out = append(out, TenantUsage{
			TenantID:           t.ID,
			Slug:               t.Slug,
			DeliveriesPerHour:  t.DeliveriesPerHour,
			SuccessfulLastHour: okN,
			FailedLastHour:     failN,
			Pending:            pending,
			DLQ:                dlq,
			QuotaRemaining:     remain,
		})
	}
	return out, nil
}

func countStatus(st *store.Store, tenantID, status string) (int, error) {
	var n int
	err := st.DB().QueryRow(
		`SELECT COUNT(*) FROM events WHERE tenant_id=? AND status=?`, tenantID, status,
	).Scan(&n)
	return n, err
}
