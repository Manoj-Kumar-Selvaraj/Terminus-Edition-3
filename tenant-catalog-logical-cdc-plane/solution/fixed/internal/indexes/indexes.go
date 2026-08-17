package indexes

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/snapshot"
	"catalog/internal/store"
	"catalog/internal/visibility"
	"catalog/internal/wal"
)

func Rebuild(st *store.Store, snapshotID int64) error {
	idx, err := Expected(st, snapshotID)
	if err != nil {
		return err
	}
	return st.WriteIndexes(idx)
}

func Expected(st *store.Store, snapshotID int64) (map[string]map[string]string, error) {
	versions, err := st.LoadVersions()
	if err != nil {
		return nil, err
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return nil, err
	}
	if snapshotID <= 0 {
		var max int64
		for id := range wal.CommittedTxns(recs) {
			if id > max {
				max = id
			}
		}
		snapshotID = max
	}
	rows := visibility.SnapshotVisible(versions, snapshotID, nil, wal.CommittedTxns(recs))
	_ = snapshot.Visible
	idx := map[string]map[string]string{"sku_code": {}, "offer_code": {}}
	for _, v := range rows {
		left, right, ok := schema.UniqueSpec(v.Table)
		if !ok {
			continue
		}
		key := model.UniqueKey(schema.Str(v.Payload, left), schema.Str(v.Payload, right))
		bucket := "sku_code"
		if v.Table == model.TableOffer {
			bucket = "offer_code"
		}
		idx[bucket][key] = v.PK
	}
	return idx, nil
}

func Match(st *store.Store, snapshotID int64) (bool, error) {
	got, err := st.LoadIndexes()
	if err != nil {
		return false, err
	}
	want, err := Expected(st, snapshotID)
	if err != nil {
		return false, err
	}
	return equalIdx(got, want), nil
}

func equalIdx(a, b map[string]map[string]string) bool {
	for _, bucket := range []string{"sku_code", "offer_code"} {
		left, right := a[bucket], b[bucket]
		if len(left) != len(right) {
			return false
		}
		for k, v := range left {
			if right[k] != v {
				return false
			}
		}
	}
	return true
}
