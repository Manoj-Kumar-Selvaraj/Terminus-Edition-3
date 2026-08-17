package txn

import (
	"catalog/internal/heap"
	"catalog/internal/model"
)

func beforeAfter(op, table, pk string, payload map[string]any, byKey map[string]model.RowVersion) (before, after map[string]any) {
	if prev, ok := byKey[model.RowKey(table, pk)]; ok {
		before = model.CopyMap(prev.Payload)
	}
	switch op {
	case "insert":
		return nil, model.CopyMap(payload)
	case "update":
		return before, heap.PayloadAfter("update", before, payload)
	case "delete":
		return before, nil
	default:
		return before, model.CopyMap(payload)
	}
}

func overlayVisible(byKey map[string]model.RowVersion, m model.Mutation) {
	key := model.RowKey(m.Table, m.PK)
	switch m.Op {
	case "delete":
		delete(byKey, key)
	case "insert":
		byKey[key] = model.RowVersion{Table: m.Table, PK: m.PK, Payload: model.CopyMap(m.Payload)}
	case "update":
		cur := model.RowVersion{Table: m.Table, PK: m.PK, Payload: map[string]any{}}
		if prev, ok := byKey[key]; ok {
			cur.Payload = model.CopyMap(prev.Payload)
		}
		for k, v := range m.Payload {
			cur.Payload[k] = v
		}
		byKey[key] = cur
	}
}
