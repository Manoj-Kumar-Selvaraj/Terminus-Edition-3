package indexes

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
)

// Rebuild is the starter implementation: every version, slash-separated keys.
func Rebuild(st *store.Store, snapshot int64) error {
	_ = snapshot
	versions, err := st.LoadVersions()
	if err != nil {
		return err
	}
	idx := map[string]map[string]string{"sku_code": {}, "offer_code": {}}
	for _, v := range versions {
		left, right, ok := schema.UniqueSpec(v.Table)
		if !ok {
			continue
		}
		key := schema.Str(v.Payload, left) + "/" + schema.Str(v.Payload, right)
		bucket := "sku_code"
		if v.Table == model.TableOffer {
			bucket = "offer_code"
		}
		idx[bucket][key] = v.PK
	}
	return st.WriteIndexes(idx)
}

func Expected(st *store.Store, snapshot int64) (map[string]map[string]string, error) {
	_ = st
	_ = snapshot
	return map[string]map[string]string{"sku_code": {}, "offer_code": {}}, nil
}

func Match(st *store.Store, snapshot int64) (bool, error) {
	got, err := st.LoadIndexes()
	if err != nil {
		return false, err
	}
	want, err := Expected(st, snapshot)
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
