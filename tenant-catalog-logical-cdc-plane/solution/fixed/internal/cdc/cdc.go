package cdc

import (
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/store"
	"catalog/internal/wal"
	"encoding/json"
	"os"
)

func Decode(st *store.Store, confirmedLSN int64) ([]model.CDCEvent, error) {
	recs, err := st.LoadWAL()
	if err != nil {
		return nil, err
	}
	committed := wal.CommittedTxns(recs)
	var out []model.CDCEvent
	for _, rec := range recs {
		if rec.LSN <= confirmedLSN {
			continue
		}
		op := model.KindOp(rec.Kind)
		if op == "" {
			continue
		}
		if _, ok := committed[rec.TxnID]; !ok {
			continue
		}
		if !wal.HasCommit(recs, rec.TxnID) {
			continue
		}
		out = append(out, model.CDCEvent{
			LSN:    rec.LSN,
			TxnID:  rec.TxnID,
			Epoch:  rec.Epoch,
			Table:  rec.Table,
			Op:     op,
			PK:     rec.PK,
			Before: rec.Before,
			After:  rec.After,
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
