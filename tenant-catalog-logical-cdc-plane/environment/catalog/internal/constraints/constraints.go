package constraints

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
)

// Check is the starter implementation: replica-lag unique/FK, skips frozen/hold aggregate.
func Check(st *store.Store, snapshot, txnID int64, mutations []model.Mutation) (*model.Reject, error) {
	_ = snapshot
	skus, err := st.ReplicaRows(model.TableSKU)
	if err != nil {
		return nil, err
	}
	for _, m := range mutations {
		if !schema.KnownTable(m.Table) {
			return &model.Reject{TxnID: txnID, Code: "CHECK_FAIL", Table: m.Table, PK: m.PK, Detail: "unknown table"}, nil
		}
		if m.Op == "insert" && m.Table == model.TableSKU {
			code := schema.Str(m.Payload, "sku_code")
			for _, row := range skus {
				if schema.Str(row, "sku_id") == code {
					return &model.Reject{TxnID: txnID, Code: "UNIQUE_CONFLICT", Table: m.Table, PK: m.PK, Detail: code}, nil
				}
			}
		}
		if m.Table == model.TableOffer {
			if qty, ok := schema.IntField(m.Payload, "qty_on_hand"); ok && qty < 0 {
				return &model.Reject{TxnID: txnID, Code: "CHECK_FAIL", Table: m.Table, PK: m.PK, Detail: "qty_on_hand"}, nil
			}
			if m.Op == "insert" {
				skuID := schema.Str(m.Payload, "sku_id")
				found := false
				for _, row := range skus {
					if schema.Str(row, "sku_id") == skuID {
						found = true
						break
					}
				}
				if !found {
					return &model.Reject{TxnID: txnID, Code: "FK_MISSING", Table: m.Table, PK: m.PK, Detail: skuID}, nil
				}
			}
		}
	}
	return nil, nil
}
