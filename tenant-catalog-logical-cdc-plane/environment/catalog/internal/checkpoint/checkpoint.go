package checkpoint

import (
	"encoding/json"
	"os"

	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/store"
)

type HeapRow struct {
	Table     string         `json:"table"`
	PK        string         `json:"pk"`
	Xmin      int64          `json:"xmin"`
	Xmax      *int64         `json:"xmax"`
	Committed bool           `json:"committed"`
	LSN       int64          `json:"lsn"`
	Payload   map[string]any `json:"payload"`
}

type Doc struct {
	LSN    int64     `json:"lsn"`
	TxnID  int64     `json:"txn_id"`
	Epoch  int64     `json:"epoch"`
	Heap   []HeapRow `json:"heap"`
}

func FromVersions(lsn, txnID, epoch int64, rows []model.RowVersion) Doc {
	heap := make([]HeapRow, 0, len(rows))
	for _, v := range rows {
		heap = append(heap, HeapRow{
			Table:     v.Table,
			PK:        v.PK,
			Xmin:      v.Xmin,
			Xmax:      v.Xmax,
			Committed: v.Committed,
			LSN:       v.LSN,
			Payload:   model.CopyMap(v.Payload),
		})
	}
	return Doc{LSN: lsn, TxnID: txnID, Epoch: epoch, Heap: heap}
}

func ToVersions(doc Doc) []model.RowVersion {
	out := make([]model.RowVersion, 0, len(doc.Heap))
	for _, row := range doc.Heap {
		out = append(out, model.RowVersion{
			Table:     row.Table,
			PK:        row.PK,
			Xmin:      row.Xmin,
			Xmax:      row.Xmax,
			Committed: row.Committed,
			LSN:       row.LSN,
			Payload:   model.CopyMap(row.Payload),
		})
	}
	return out
}

func Write(doc Doc) error {
	b, err := json.Marshal(doc)
	if err != nil {
		return err
	}
	return os.WriteFile(paths.Checkpoint(), append(b, '\n'), 0o644)
}

func Load() (Doc, error) {
	b, err := os.ReadFile(paths.Checkpoint())
	if err != nil {
		if os.IsNotExist(err) {
			return Doc{}, nil
		}
		return Doc{}, err
	}
	var doc Doc
	if err := json.Unmarshal(b, &doc); err != nil {
		raw, err2 := storeFallback()
		if err2 != nil {
			return Doc{}, err
		}
		return raw, nil
	}
	return doc, nil
}

func storeFallback() (Doc, error) {
	st := store.New()
	raw, err := st.LoadCheckpoint()
	if err != nil {
		return Doc{}, err
	}
	doc := Doc{
		LSN:   store.AsInt64(raw["lsn"]),
		TxnID: store.AsInt64(raw["txn_id"]),
		Epoch: store.AsInt64(raw["epoch"]),
	}
	return doc, nil
}

func LSNOf(raw map[string]any) int64 {
	return store.AsInt64(raw["lsn"])
}
