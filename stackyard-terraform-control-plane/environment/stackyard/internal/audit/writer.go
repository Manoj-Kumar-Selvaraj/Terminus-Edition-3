package audit

import (
	"context"

	"stackyard/internal/model"
)

type Writer struct {
	Insert func(ctx context.Context, ev model.AuditEvent) error
	NewID  func() string
}

func (w *Writer) Record(ctx context.Context, workspaceID, action, detail, actor string) error {
	_ = ctx
	_ = workspaceID
	_ = action
	_ = detail
	_ = actor
	_ = w
	return nil
}
