package recover

import (
	"catalog/internal/checkpoint"
	"catalog/internal/indexes"
	"catalog/internal/model"
	"catalog/internal/store"
)

// Recover is the starter implementation: restore checkpoint, install uncommitted
// WAL mutations, and bump the replica epoch.
func Recover(st *store.Store) error {
	doc, err := checkpoint.Load()
	if err != nil {
		return err
	}
	versions := checkpoint.ToVersions(doc)
	recs, err := st.LoadWAL()
	if err != nil {
		return err
	}
	for _, rec := range recs {
		if rec.LSN <= doc.LSN {
			continue
		}
		if rec.Kind != "INSERT" && rec.Kind != "UPDATE" && rec.Kind != "DELETE" {
			continue
		}
		versions = applyRec(versions, rec)
	}
	if err := st.ReplaceVersions(versions); err != nil {
		return err
	}
	slot, err := st.LoadSlot()
	if err != nil {
		return err
	}
	slot.Epoch++
	if err := st.WriteSlot(slot); err != nil {
		return err
	}
	return indexes.Rebuild(st, 0)
}

func applyRec(versions []model.RowVersion, rec model.WalRecord) []model.RowVersion {
	switch rec.Kind {
	case "INSERT":
		return append(versions, model.RowVersion{
			Table: rec.Table, PK: rec.PK, Xmin: rec.TxnID, Committed: false, LSN: rec.LSN, Payload: model.CopyMap(rec.After),
		})
	case "UPDATE":
		xmax := rec.TxnID
		for i := range versions {
			if versions[i].Table == rec.Table && versions[i].PK == rec.PK && versions[i].Xmax == nil {
				versions[i].Xmax = &xmax
			}
		}
		return append(versions, model.RowVersion{
			Table: rec.Table, PK: rec.PK, Xmin: rec.TxnID, Committed: false, LSN: rec.LSN, Payload: model.CopyMap(rec.After),
		})
	case "DELETE":
		xmax := rec.TxnID
		for i := range versions {
			if versions[i].Table == rec.Table && versions[i].PK == rec.PK && versions[i].Xmax == nil {
				versions[i].Xmax = &xmax
			}
		}
	}
	return versions
}
