package report

import (
	"outbox/internal/model"
	"outbox/internal/store"
)

type EndpointHealth struct {
	EndpointID   string  `json:"endpoint_id"`
	TenantID     string  `json:"tenant_id"`
	Name         string  `json:"name"`
	Enabled      bool    `json:"enabled"`
	Paused       bool    `json:"paused"`
	Delivered    int     `json:"delivered"`
	Failed       int     `json:"failed"`
	DLQ          int     `json:"dlq"`
	Pending      int     `json:"pending"`
	SuccessRate  float64 `json:"success_rate"`
}

func EndpointHealthReport(st *store.Store, tenantID string) ([]EndpointHealth, error) {
	eps, err := st.ListEndpoints(tenantID)
	if err != nil {
		return nil, err
	}
	var out []EndpointHealth
	for _, ep := range eps {
		h := EndpointHealth{
			EndpointID: ep.ID,
			TenantID:   ep.TenantID,
			Name:       ep.Name,
			Enabled:    ep.Enabled,
			Paused:     ep.Paused,
		}
		for _, stName := range []string{model.StatusDelivered, model.StatusPending, model.StatusDLQ} {
			var n int
			err := st.DB().QueryRow(
				`SELECT COUNT(*) FROM events WHERE endpoint_id=? AND status=?`, ep.ID, stName,
			).Scan(&n)
			if err != nil {
				return nil, err
			}
			switch stName {
			case model.StatusDelivered:
				h.Delivered = n
			case model.StatusPending:
				h.Pending = n
			case model.StatusDLQ:
				h.DLQ = n
			}
		}
		err := st.DB().QueryRow(
			`SELECT COUNT(*) FROM delivery_attempts a
			 JOIN events e ON e.id=a.event_id
			 WHERE e.endpoint_id=? AND a.outcome=?`, ep.ID, model.OutcomeFailed,
		).Scan(&h.Failed)
		if err != nil {
			return nil, err
		}
		total := h.Delivered + h.Failed
		if total > 0 {
			h.SuccessRate = float64(h.Delivered) / float64(total)
		}
		out = append(out, h)
	}
	return out, nil
}
