package cdcevent

import (
	"fmt"
	"sort"

	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
)

// Event is a typed view of one CDC JSONL object.
type Event struct {
	LSN    int64
	TxnID  int64
	Epoch  int64
	Table  string
	Op     string
	PK     string
	Before map[string]any
	After  map[string]any
	Raw    map[string]any
}

// Parse converts a loose JSON map into a typed CDC event.
func Parse(rec map[string]any) (Event, error) {
	ev := Event{
		LSN:    store.AsInt64(rec["lsn"]),
		TxnID:  store.AsInt64(rec["txn_id"]),
		Epoch:  store.AsInt64(rec["epoch"]),
		Table:  store.AsString(rec["table"]),
		Op:     store.AsString(rec["op"]),
		PK:     store.AsString(rec["pk"]),
		Raw:    rec,
	}
	if before, ok := rec["before"].(map[string]any); ok {
		ev.Before = model.CopyMap(before)
	}
	if after, ok := rec["after"].(map[string]any); ok {
		ev.After = model.CopyMap(after)
	}
	if ev.LSN <= 0 || ev.TxnID <= 0 {
		return Event{}, fmt.Errorf("cdc event requires positive lsn and txn_id")
	}
	if !schema.KnownTable(ev.Table) {
		return Event{}, fmt.Errorf("unknown cdc table %q", ev.Table)
	}
	if ev.Op != "insert" && ev.Op != "update" && ev.Op != "delete" {
		return Event{}, fmt.Errorf("unknown cdc op %q", ev.Op)
	}
	if ev.PK == "" {
		return Event{}, fmt.Errorf("cdc event missing pk")
	}
	if ev.Op == "insert" && ev.After == nil {
		return Event{}, fmt.Errorf("insert requires after image")
	}
	if ev.Op == "delete" && ev.Before == nil && ev.After != nil {
		// delete may carry before only; after must be null/absent
		return Event{}, fmt.Errorf("delete must not carry after image")
	}
	if ev.Op == "update" && (ev.Before == nil || ev.After == nil) {
		return Event{}, fmt.Errorf("update requires before and after")
	}
	return ev, nil
}

// ParseAll parses a batch; on the first hard error it returns what was accepted plus the error.
func ParseAll(records []map[string]any) ([]Event, error) {
	out := make([]Event, 0, len(records))
	for i, rec := range records {
		ev, err := Parse(rec)
		if err != nil {
			return out, fmt.Errorf("cdc record %d: %w", i, err)
		}
		out = append(out, ev)
	}
	return out, nil
}

// SoftParse keeps malformed rows as zero Events with Raw retained for fencing diagnostics.
func SoftParse(records []map[string]any) []Event {
	out := make([]Event, 0, len(records))
	for _, rec := range records {
		ev, err := Parse(rec)
		if err != nil {
			out = append(out, Event{
				LSN:   store.AsInt64(rec["lsn"]),
				TxnID: store.AsInt64(rec["txn_id"]),
				Epoch: store.AsInt64(rec["epoch"]),
				Table: store.AsString(rec["table"]),
				Op:    store.AsString(rec["op"]),
				PK:    store.AsString(rec["pk"]),
				Raw:   rec,
			})
			continue
		}
		out = append(out, ev)
	}
	return out
}

// GroupByTxn groups events by txn_id preserving first-seen order of txn keys.
func GroupByTxn(events []Event) [][]Event {
	order := []int64{}
	seen := map[int64]int{}
	var groups [][]Event
	for _, ev := range events {
		idx, ok := seen[ev.TxnID]
		if !ok {
			seen[ev.TxnID] = len(groups)
			order = append(order, ev.TxnID)
			groups = append(groups, []Event{ev})
			continue
		}
		groups[idx] = append(groups[idx], ev)
	}
	_ = order
	return groups
}

// SortByLSN returns a copy sorted by LSN ascending.
func SortByLSN(events []Event) []Event {
	out := append([]Event(nil), events...)
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].LSN == out[j].LSN {
			return out[i].TxnID < out[j].TxnID
		}
		return out[i].LSN < out[j].LSN
	})
	return out
}

// ToMaps converts typed events back to JSON-shaped maps for apply helpers.
func ToMaps(events []Event) []map[string]any {
	out := make([]map[string]any, 0, len(events))
	for _, ev := range events {
		if ev.Raw != nil {
			out = append(out, ev.Raw)
			continue
		}
		m := map[string]any{
			"lsn":     ev.LSN,
			"txn_id":  ev.TxnID,
			"epoch":   ev.Epoch,
			"table":   ev.Table,
			"op":      ev.Op,
			"pk":      ev.PK,
			"before":  ev.Before,
			"after":   ev.After,
		}
		out = append(out, m)
	}
	return out
}

// FromModel adapts model.CDCEvent values produced by decode.
func FromModel(events []model.CDCEvent) []Event {
	out := make([]Event, 0, len(events))
	for _, e := range events {
		out = append(out, Event{
			LSN:    e.LSN,
			TxnID:  e.TxnID,
			Epoch:  e.Epoch,
			Table:  e.Table,
			Op:     e.Op,
			PK:     e.PK,
			Before: model.CopyMap(e.Before),
			After:  model.CopyMap(e.After),
		})
	}
	return out
}

// FKRank returns apply parent rank for a table.
func FKRank(table string) int {
	switch table {
	case model.TableTenant:
		return 0
	case model.TableSKU:
		return 1
	case model.TableOffer:
		return 2
	case model.TableHold:
		return 3
	default:
		return 99
	}
}
