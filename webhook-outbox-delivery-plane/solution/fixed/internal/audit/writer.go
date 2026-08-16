package audit

import (
	"outbox/internal/store"
)

type Writer struct {
	Store *store.Store
}

func (w *Writer) Write(action, entityType, entityID, actor string, detail map[string]any) error {
	_, err := w.Store.InsertAudit(action, entityType, entityID, actor, detail)
	return err
}
