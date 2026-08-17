package snapshot

import (
	"catalog/internal/model"
	"catalog/internal/store"
	"catalog/internal/visibility"
	"catalog/internal/wal"
)

func CommittedSet(st *store.Store) (map[int64]struct{}, error) {
	recs, err := st.LoadWAL()
	if err != nil {
		return nil, err
	}
	return wal.CommittedTxns(recs), nil
}

func LatestCommitted(st *store.Store) (int64, error) {
	set, err := CommittedSet(st)
	if err != nil {
		return 0, err
	}
	var max int64
	for id := range set {
		if id > max {
			max = id
		}
	}
	return max, nil
}

// Visible is the starter implementation: latest xmax-null row, including uncommitted.
func Visible(st *store.Store, snapshot int64, writer *int64) ([]model.RowVersion, error) {
	versions, err := st.LoadVersions()
	if err != nil {
		return nil, err
	}
	_ = snapshot
	_ = writer
	return visibility.LatestXmaxNull(versions), nil
}

func VisibleMap(st *store.Store, snapshot int64, writer *int64) (map[string]model.RowVersion, error) {
	rows, err := Visible(st, snapshot, writer)
	if err != nil {
		return nil, err
	}
	out := map[string]model.RowVersion{}
	for _, v := range rows {
		out[v.Table+"/"+v.PK] = v
	}
	return out, nil
}
