package applyorder

import (
	"sort"

	"catalog/internal/schema"
)

func Order(records []map[string]any, reverseFK bool) []map[string]any {
	items, txnOrder := group(records)
	var out []map[string]any
	for _, txn := range txnOrder {
		batch := collect(items, txn)
		sortBatch(batch, reverseFK)
		for _, it := range batch {
			out = append(out, it.rec)
		}
	}
	return out
}

type pair struct {
	txn int64
	lsn int64
	rec map[string]any
}

func group(records []map[string]any) ([]pair, []int64) {
	var items []pair
	order := []int64{}
	seen := map[int64]bool{}
	for _, rec := range records {
		txn := asInt(rec["txn_id"])
		if !seen[txn] {
			seen[txn] = true
			order = append(order, txn)
		}
		items = append(items, pair{txn: txn, lsn: asInt(rec["lsn"]), rec: rec})
	}
	return items, order
}

func collect(items []pair, txn int64) []pair {
	var batch []pair
	for _, it := range items {
		if it.txn == txn {
			batch = append(batch, it)
		}
	}
	return batch
}

func sortBatch(batch []pair, reverseFK bool) {
	sort.Slice(batch, func(i, j int) bool {
		ti := schema.FKRank(str(batch[i].rec["table"]))
		tj := schema.FKRank(str(batch[j].rec["table"]))
		if reverseFK {
			ti, tj = -ti, -tj
		}
		if ti != tj {
			return ti < tj
		}
		return batch[i].lsn < batch[j].lsn
	})
}

func asInt(v any) int64 {
	switch n := v.(type) {
	case float64:
		return int64(n)
	case int64:
		return n
	case int:
		return int64(n)
	default:
		return 0
	}
}

func str(v any) string {
	s, _ := v.(string)
	return s
}
