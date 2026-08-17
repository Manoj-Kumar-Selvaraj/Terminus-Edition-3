package recover

import (
	"catalog/internal/checkpoint"
	"catalog/internal/heap"
	"catalog/internal/indexes"
	"catalog/internal/model"
	"catalog/internal/store"
	"catalog/internal/wal"
)

func Recover(st *store.Store) error {
	doc, err := checkpoint.Load()
	if err != nil {
		return err
	}
	if err := st.ReplaceVersions(checkpoint.ToVersions(doc)); err != nil {
		return err
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return err
	}
	committed := wal.CommittedTxns(recs)
	for _, rec := range recs {
		if rec.LSN <= doc.LSN {
			continue
		}
		if rec.Kind != "INSERT" && rec.Kind != "UPDATE" && rec.Kind != "DELETE" {
			continue
		}
		if _, ok := committed[rec.TxnID]; !ok {
			continue
		}
		if err := heap.InstallRecord(st, rec); err != nil {
			return err
		}
	}
	_ = model.Tables
	return indexes.Rebuild(st, doc.TxnID)
}
