package visibility

import "catalog/internal/model"

func LatestXmaxNull(versions []model.RowVersion) []model.RowVersion {
	chosen := map[string]model.RowVersion{}
	for _, v := range versions {
		if v.Xmax != nil {
			continue
		}
		key := v.Table + "/" + v.PK
		prev, ok := chosen[key]
		if !ok || v.LSN >= prev.LSN {
			chosen[key] = v
		}
	}
	out := make([]model.RowVersion, 0, len(chosen))
	for _, v := range chosen {
		out = append(out, v)
	}
	return out
}

func SnapshotVisible(versions []model.RowVersion, snapshot int64, writer *int64, committed map[int64]struct{}) []model.RowVersion {
	chosen := map[string]model.RowVersion{}
	for _, v := range versions {
		if !xminOK(v, snapshot, writer, committed) {
			continue
		}
		if xmaxHides(v, snapshot, writer, committed) {
			continue
		}
		key := v.Table + "/" + v.PK
		prev, ok := chosen[key]
		if !ok || v.Xmin > prev.Xmin || (v.Xmin == prev.Xmin && v.LSN > prev.LSN) {
			chosen[key] = v
		}
	}
	out := make([]model.RowVersion, 0, len(chosen))
	for _, v := range chosen {
		out = append(out, v)
	}
	return out
}

func xminOK(v model.RowVersion, snapshot int64, writer *int64, committed map[int64]struct{}) bool {
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
