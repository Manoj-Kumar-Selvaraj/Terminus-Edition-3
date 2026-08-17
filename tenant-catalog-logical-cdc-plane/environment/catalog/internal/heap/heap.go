package heap

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
)

func Current(versions []model.RowVersion, table, pk string, snapshot int64, writer *int64, committed map[int64]struct{}) (model.RowVersion, bool) {
	var best model.RowVersion
	found := false
	for _, v := range versions {
		if v.Table != table || v.PK != pk {
			continue
		}
		if !xminVisible(v, snapshot, writer, committed) {
			continue
		}
		if xmaxHides(v, snapshot, writer, committed) {
			continue
		}
		if !found || v.Xmin > best.Xmin || (v.Xmin == best.Xmin && v.LSN > best.LSN) {
			best = v
			found = true
		}
	}
	return best, found
}

func xminVisible(v model.RowVersion, snapshot int64, writer *int64, committed map[int64]struct{}) bool {
	if v.Xmin > snapshot {
		return false
	}
	if writer != nil && v.Xmin == *writer {
		return true
	}
	_, ok := committed[v.Xmin]
	return ok || v.Committed
}

func xmaxHides(v model.RowVersion, snapshot int64, writer *int64, committed map[int64]struct{}) bool {
	if v.Xmax == nil {
		return false
	}
	xmax := *v.Xmax
	if writer != nil && xmax == *writer {
		return true
	}
	if _, ok := committed[xmax]; !ok {
		return false
	}
	return xmax <= snapshot
}

func Install(st *store.Store, txnID int64, mutations []model.Mutation, recs []model.WalRecord) error {
	versions, err := st.LoadVersions()
	if err != nil {
		return err
	}
	committed := map[int64]struct{}{}
	for _, r := range recs {
		if r.Kind == "COMMIT" {
			committed[r.TxnID] = struct{}{}
		}
	}
	writer := txnID
	lsnByPK := mutationLSN(recs, txnID)
	for _, m := range mutations {
		lsn := lsnByPK[model.RowKey(m.Table, m.PK)]
		cur, ok := Current(versions, m.Table, m.PK, txnID, &writer, committed)
		switch m.Op {
		case "insert":
			payload := model.CopyMap(m.Payload)
			v := model.RowVersion{Table: m.Table, PK: m.PK, Xmin: txnID, Committed: true, LSN: lsn, Payload: payload}
			if err := st.UpsertVersion(v); err != nil {
				return err
			}
			versions = append(versions, v)
		case "update":
			if ok {
				if err := st.SetXmax(cur.Table, cur.PK, cur.Xmin, txnID); err != nil {
					return err
				}
			}
			merged := model.CopyMap(cur.Payload)
			for k, val := range m.Payload {
				merged[k] = val
			}
			v := model.RowVersion{Table: m.Table, PK: m.PK, Xmin: txnID, Committed: true, LSN: lsn, Payload: merged}
			if err := st.UpsertVersion(v); err != nil {
				return err
			}
			versions = append(versions, v)
		case "delete":
			if ok {
				if err := st.SetXmax(cur.Table, cur.PK, cur.Xmin, txnID); err != nil {
					return err
				}
			}
		}
	}
	return st.MarkCommitted(txnID)
}

func InstallRecord(st *store.Store, rec model.WalRecord) error {
	op := model.KindOp(rec.Kind)
	if op == "" {
		return nil
	}
	m := model.Mutation{Op: op, Table: rec.Table, PK: rec.PK, Payload: rec.After}
	if op == "delete" {
		m.Payload = map[string]any{}
	}
	return Install(st, rec.TxnID, []model.Mutation{m}, []model.WalRecord{rec, {Kind: "COMMIT", TxnID: rec.TxnID, LSN: rec.LSN}})
}

func mutationLSN(recs []model.WalRecord, txnID int64) map[string]int64 {
	out := map[string]int64{}
	for _, r := range recs {
		if r.TxnID != txnID {
			continue
		}
		if r.Kind != "INSERT" && r.Kind != "UPDATE" && r.Kind != "DELETE" {
			continue
		}
		out[model.RowKey(r.Table, r.PK)] = r.LSN
	}
	return out
}

func PayloadAfter(op string, before, after map[string]any) map[string]any {
	if op == "delete" {
		return nil
	}
	if op == "insert" {
		return model.CopyMap(after)
	}
	merged := model.CopyMap(before)
	for k, v := range after {
		merged[k] = v
	}
	if merged == nil {
		return model.CopyMap(after)
	}
	return merged
}

func PKField(table string) string {
	switch table {
	case model.TableTenant:
		return "tenant_id"
	case model.TableSKU:
		return "sku_id"
	case model.TableOffer:
		return "offer_id"
	case model.TableHold:
		return "hold_id"
	default:
		return ""
	}
}

func AlignPK(table, pk string, payload map[string]any) map[string]any {
	out := model.CopyMap(payload)
	if out == nil {
		out = map[string]any{}
	}
	if field := PKField(table); field != "" {
		if schema.Str(out, field) == "" {
			out[field] = pk
		}
	}
	return out
}
