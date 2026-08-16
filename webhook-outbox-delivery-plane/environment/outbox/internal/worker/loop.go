package worker

import (
	"context"
	"time"

	"outbox/internal/model"
	"outbox/internal/service"
	"outbox/internal/store"
)

type Loop struct {
	Store  *store.Store
	Svc    *service.Outbox
	Owner  string
	Every  time.Duration
	Batch  int
}

func (l *Loop) RunOnce(ctx context.Context) (int, error) {
	if l.Batch < 1 {
		l.Batch = 10
	}
	if l.Owner == "" {
		l.Owner = "worker-1"
	}
	rows, err := l.Store.DB().Query(
		`SELECT id FROM events WHERE status=? AND next_attempt_at<=? ORDER BY next_attempt_at ASC LIMIT ?`,
		model.StatusPending, model.FormatTime(l.Store.Now()), l.Batch,
	)
	if err != nil {
		return 0, err
	}
	defer rows.Close()
	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return 0, err
		}
		ids = append(ids, id)
	}
	done := 0
	for _, id := range ids {
		if _, err := l.Svc.Claim(id, l.Owner, 30); err != nil {
			continue
		}
		if _, err := l.Svc.Deliver(ctx, id, l.Owner); err != nil {
			continue
		}
		done++
	}
	return done, nil
}

func (l *Loop) Start(ctx context.Context) {
	if l.Every <= 0 {
		l.Every = time.Second
	}
	t := time.NewTicker(l.Every)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			_, _ = l.RunOnce(ctx)
		}
	}
}
