package cdc

import (
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/store"
	"encoding/json"
	"os"
)

// Decode is the starter implementation: heap scan of sku rows with row numbers as LSN.
func Decode(st *store.Store, confirmedLSN int64) ([]model.CDCEvent, error) {
	_ = confirmedLSN
	versions, err := st.LoadVersions()
	if err != nil {
		return nil, err
	}
	var out []model.CDCEvent
	n := int64(0)
	for _, v := range versions {
		if v.Table != model.TableSKU {
			continue
		}
		n++
		op := "insert"
		if v.Xmax != nil {
			op = "update"
		}
		out = append(out, model.CDCEvent{
			LSN:    n,
			TxnID:  v.Xmin,
			Epoch:  1,
			Table:  v.Table,
			Op:     op,
			PK:     v.PK,
			Before: nil,
			After:  model.CopyMap(v.Payload),
		})
	}
	return out, nil
}

func Write(events []model.CDCEvent) error {
	f, err := os.Create(paths.CDC())
	if err != nil {
		return err
	}
	defer f.Close()
	for _, ev := range events {
		b, err := json.Marshal(ev)
		if err != nil {
			return err
		}
		if _, err := f.Write(append(b, '\n')); err != nil {
			return err
		}
	}
	return nil
}
