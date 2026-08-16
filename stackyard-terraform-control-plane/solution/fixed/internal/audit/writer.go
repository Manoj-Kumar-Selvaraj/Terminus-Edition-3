package audit

import (
	"context"
	"fmt"
	"time"

	"stackyard/internal/model"
)

type Writer struct {
	Insert func(ctx context.Context, ev model.AuditEvent) error
	NewID  func() string
}

func (w *Writer) Record(ctx context.Context, workspaceID, action, detail, actor string) error {
	if w == nil || w.Insert == nil || w.NewID == nil {
		return fmt.Errorf("audit writer not configured")
	}
	if actor == "" {
		actor = "system"
	}
	ev := model.AuditEvent{
		ID:          w.NewID(),
		WorkspaceID: workspaceID,
		Action:      action,
		Detail:      detail,
		Actor:       actor,
		CreatedAt:   time.Now().UTC(),
	}
	return w.Insert(ctx, ev)
}
