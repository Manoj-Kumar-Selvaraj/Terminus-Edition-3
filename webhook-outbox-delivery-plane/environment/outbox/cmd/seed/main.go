package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"outbox/internal/clock"
	"outbox/internal/config"
	"outbox/internal/model"
	"outbox/internal/store"
)

// Seeds 12_000+ primary business records (events + delivery_attempts) deterministically.
func main() {
	cfg := config.Load()
	_ = os.MkdirAll(cfg.Data, 0o755)
	st, err := store.Open(cfg.DBPath, cfg.SchemaPath(), clock.Fixed{T: time.Date(2024, 6, 1, 12, 0, 0, 0, time.UTC)})
	if err != nil {
		fatal(err)
	}
	defer st.Close()

	tenants := []struct {
		name, slug string
		quota      int
	}{
		{"Acme Retail", "acme", 5000},
		{"Globex Shipping", "globex", 2000},
		{"Initech Payments", "initech", 1500},
		{"Umbrella Labs", "umbrella", 800},
		{"Stark Logistics", "stark", 1200},
		{"Wayne Health", "wayne", 900},
	}

	var tenantIDs []string
	var endpoints []model.Endpoint
	for _, t := range tenants {
		ten, err := st.EnsureTenant(t.name, t.slug, t.quota)
		if err != nil {
			fatal(err)
		}
		tenantIDs = append(tenantIDs, ten.ID)
		for i := 0; i < 3; i++ {
			ep, err := st.CreateEndpoint(
				ten.ID,
				fmt.Sprintf("%s-hook-%d", t.slug, i),
				fmt.Sprintf("http://127.0.0.1:9/%s/%d", t.slug, i),
				fmt.Sprintf("secret-%s-%d", t.slug, i),
				true,
				5,
			)
			if err != nil {
				fatal(err)
			}
			endpoints = append(endpoints, ep)
		}
	}

	statuses := []string{
		model.StatusPending, model.StatusPending, model.StatusPending,
		model.StatusDelivered, model.StatusDelivered,
		model.StatusClaimed, model.StatusDLQ, model.StatusFailed,
	}

	const targetEvents = 10000
	base := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	for i := 0; i < targetEvents; i++ {
		ep := endpoints[i%len(endpoints)]
		stStatus := statuses[i%len(statuses)]
		payload, _ := json.Marshal(map[string]any{
			"seq":     i,
			"sku":     fmt.Sprintf("SKU-%05d", i%500),
			"region":  []string{"us-east", "eu-west", "ap-south"}[i%3],
			"amount":  (i%97) + 1,
			"channel": []string{"orders", "refunds", "inventory"}[i%3],
		})
		var idem *string
		if i%11 == 0 {
			k := fmt.Sprintf("idem-%d", i)
			idem = &k
		}
		now := base.Add(time.Duration(i) * time.Minute)
		ev := model.Event{
			ID:             model.NewEventID(),
			TenantID:       ep.TenantID,
			EndpointID:     ep.ID,
			IdempotencyKey: idem,
			Status:         stStatus,
			AttemptCount:   0,
			NextAttemptAt:  now,
			CreatedAt:      now,
			UpdatedAt:      now,
		}
		if stStatus == model.StatusClaimed {
			owner := fmt.Sprintf("seed-worker-%d", i%4)
			until := now.Add(30 * time.Second)
			ev.LeaseOwner = &owner
			ev.LeaseUntil = &until
			ev.AttemptCount = 1
		}
		if stStatus == model.StatusDelivered {
			ev.AttemptCount = 1
		}
		if stStatus == model.StatusDLQ {
			ev.AttemptCount = 5
		}
		if stStatus == model.StatusFailed {
			ev.AttemptCount = 2
			ev.Status = model.StatusPending
		}
		_, err := st.DB().Exec(
			`INSERT INTO events(id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at)
			 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`,
			ev.ID, ev.TenantID, ev.EndpointID, string(payload), null(idem), ev.Status, ev.AttemptCount,
			null(ev.LeaseOwner), nullTime(ev.LeaseUntil), model.FormatTime(ev.NextAttemptAt),
			model.FormatTime(ev.CreatedAt), model.FormatTime(ev.UpdatedAt),
		)
		if err != nil {
			fatal(err)
		}

		// Attach attempt history for delivered / dlq / some pending retries.
		if stStatus == model.StatusDelivered || stStatus == model.StatusDLQ || i%7 == 0 {
			attempts := ev.AttemptCount
			if attempts < 1 {
				attempts = 1
			}
			for a := 1; a <= attempts; a++ {
				outcome := model.OutcomeFailed
				httpStatus := 500
				if stStatus == model.StatusDelivered && a == attempts {
					outcome = model.OutcomeDelivered
					httpStatus = 200
				}
				attID := model.NewAttemptID()
				at := now.Add(time.Duration(a) * time.Second)
				_, err := st.DB().Exec(
					`INSERT INTO delivery_attempts(id,event_id,tenant_id,attempt_no,outcome,http_status,error,created_at)
					 VALUES(?,?,?,?,?,?,?,?)`,
					attID, ev.ID, ev.TenantID, a, outcome, httpStatus, "", model.FormatTime(at),
				)
				if err != nil {
					fatal(err)
				}
			}
		}
	}

	// Extra attempt-only history rows to push primary business records well past 12k.
	for i := 0; i < 2500; i++ {
		ep := endpoints[i%len(endpoints)]
		attID := model.NewAttemptID()
		at := base.Add(time.Duration(i) * time.Hour)
		outcome := model.OutcomeDelivered
		if i%5 == 0 {
			outcome = model.OutcomeFailed
		}
		// synthetic attempt tied to first event pattern — use a placeholder event from same tenant via subquery-less fixed id write
		// Create a tiny companion event for orphan-free FK.
		payload, _ := json.Marshal(map[string]any{"bonus": i})
		eid := model.NewEventID()
		_, err := st.DB().Exec(
			`INSERT INTO events(id,tenant_id,endpoint_id,payload,idempotency_key,status,attempt_count,lease_owner,lease_until,next_attempt_at,created_at,updated_at)
			 VALUES(?,?,?,?,NULL,?,?,NULL,NULL,?,?,?)`,
			eid, ep.TenantID, ep.ID, string(payload), model.StatusDelivered, 1,
			model.FormatTime(at), model.FormatTime(at), model.FormatTime(at),
		)
		if err != nil {
			fatal(err)
		}
		_, err = st.DB().Exec(
			`INSERT INTO delivery_attempts(id,event_id,tenant_id,attempt_no,outcome,http_status,error,created_at)
			 VALUES(?,?,?,?,?,?,?,?)`,
			attID, eid, ep.TenantID, 1, outcome, 200, "", model.FormatTime(at),
		)
		if err != nil {
			fatal(err)
		}
	}

	ec, _ := st.CountEvents()
	ac, _ := st.CountAttempts()
	fmt.Printf("seeded events=%d attempts=%d total_primary=%d db=%s\n", ec, ac, ec+ac, filepath.Clean(cfg.DBPath))
}

func null(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

func nullTime(p *time.Time) any {
	if p == nil {
		return nil
	}
	return model.FormatTime(*p)
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
