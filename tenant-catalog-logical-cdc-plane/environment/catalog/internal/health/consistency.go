package health

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
	"catalog/internal/wal"
)

func replicaConsistent(st *store.Store, visible []model.RowVersion, slot model.ReplicaSlot, durable int64) (bool, error) {
	if slot.ConfirmedLSN > durable {
		return false, nil
	}
	if slot.Epoch <= 0 {
		return false, nil
	}
	have := map[string]bool{}
	for _, v := range visible {
		have[model.RowKey(v.Table, v.PK)] = true
	}
	for _, table := range model.Tables {
		rows, err := st.ReplicaRows(table)
		if err != nil {
			return false, err
		}
		for _, row := range rows {
			pk := schema.ReplicaPK(table, row)
			if pk == "" {
				continue
			}
			if !have[model.RowKey(table, pk)] {
				return false, nil
			}
			if !replicaRowMatches(table, row, visible) {
				return false, nil
			}
		}
	}
	return true, nil
}

func replicaRowMatches(table string, row map[string]any, visible []model.RowVersion) bool {
	pk := schema.ReplicaPK(table, row)
	for _, v := range visible {
		if v.Table != table || v.PK != pk {
			continue
		}
		switch table {
		case model.TableTenant:
			return schema.Str(row, "status") == schema.Str(v.Payload, "status")
		case model.TableSKU:
			return schema.Str(row, "tenant_id") == schema.Str(v.Payload, "tenant_id") &&
				schema.Str(row, "sku_code") == schema.Str(v.Payload, "sku_code")
		case model.TableOffer:
			return schema.Str(row, "sku_id") == schema.Str(v.Payload, "sku_id") &&
				schema.Str(row, "offer_code") == schema.Str(v.Payload, "offer_code")
		case model.TableHold:
			return schema.Str(row, "offer_id") == schema.Str(v.Payload, "offer_id")
		}
	}
	return false
}

func recoveryConsistent(versions []model.RowVersion, recs []model.WalRecord, checkpointLSN int64, committed map[int64]struct{}) bool {
	uncommitted := map[string]int64{}
	for _, rec := range recs {
		if rec.LSN <= checkpointLSN {
			continue
		}
		if rec.Kind != "INSERT" && rec.Kind != "UPDATE" && rec.Kind != "DELETE" {
			continue
		}
		if _, ok := committed[rec.TxnID]; ok {
			continue
		}
		uncommitted[model.RowKey(rec.Table, rec.PK)] = rec.TxnID
	}
	for _, v := range versions {
		txn, ok := uncommitted[model.RowKey(v.Table, v.PK)]
		if !ok {
			continue
		}
		if v.Xmin == txn || (v.Xmax != nil && *v.Xmax == txn) {
			return false
		}
	}
	_ = wal.DurableLSN
	return true
}

func noUncommittedVisible(visible []model.RowVersion, committed map[int64]struct{}) bool {
	for _, v := range visible {
		if v.Committed {
			if _, ok := committed[v.Xmin]; ok {
				continue
			}
			return false
		}
		if _, ok := committed[v.Xmin]; !ok {
			return false
		}
	}
	return true
}
