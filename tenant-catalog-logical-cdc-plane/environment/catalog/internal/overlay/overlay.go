package overlay

import (
	"catalog/internal/holdqty"
	"catalog/internal/model"
	"catalog/internal/schema"
)

func Merge(visible []model.RowVersion, mutations []model.Mutation) map[string]map[string]any {
	state := map[string]map[string]any{}
	for _, v := range visible {
		state[model.RowKey(v.Table, v.PK)] = model.CopyMap(v.Payload)
	}
	for _, m := range mutations {
		key := model.RowKey(m.Table, m.PK)
		if m.Op == "delete" {
			delete(state, key)
			continue
		}
		cur := map[string]any{}
		if prev, ok := state[key]; ok {
			for k, val := range prev {
				cur[k] = val
			}
		}
		for k, val := range m.Payload {
			cur[k] = val
		}
		state[key] = cur
	}
	return state
}

func Evaluate(txnID int64, visible []model.RowVersion, mutations []model.Mutation) *model.Reject {
	state := Merge(visible, mutations)
	for _, m := range mutations {
		if !schema.KnownTable(m.Table) || !opOK(m.Op) {
			return reject(txnID, "CHECK_FAIL", m, "op")
		}
		if m.Op == "delete" {
			continue
		}
		payload := state[model.RowKey(m.Table, m.PK)]
		if payload == nil {
			return reject(txnID, "CHECK_FAIL", m, "missing payload")
		}
		if m.Table == model.TableTenant && !schema.ValidStatus(schema.Str(payload, "status")) {
			return reject(txnID, "CHECK_FAIL", m, "status")
		}
		if m.Op == "insert" {
			if miss := schema.MissingRequired(m.Table, m.Payload); miss != "" {
				return reject(txnID, "CHECK_FAIL", m, miss)
			}
			if !schema.PayloadPK(m.Table, m.PK, m.Payload) {
				return reject(txnID, "CHECK_FAIL", m, "pk mismatch")
			}
			if hasPK(visible, m.Table, m.PK) {
				return reject(txnID, "PK_CONFLICT", m, m.PK)
			}
		}
		if frozen := frozenTenant(state, m, payload); frozen != nil {
			frozen.TxnID = txnID
			return frozen
		}
		if code, detail := qtyCheck(m.Table, payload); code != "" {
			return reject(txnID, code, m, detail)
		}
		if parentTable, field, ok := schema.ParentRef(m.Table); ok {
			ppk := schema.Str(payload, field)
			if ppk == "" || state[model.RowKey(parentTable, ppk)] == nil {
				return reject(txnID, "FK_MISSING", m, ppk)
			}
		}
		if left, right, ok := schema.UniqueSpec(m.Table); ok {
			needleL, needleR := schema.Str(payload, left), schema.Str(payload, right)
			n := 0
			prefix := m.Table + "/"
			for key, row := range state {
				if row == nil || len(key) < len(prefix) || key[:len(prefix)] != prefix {
					continue
				}
				if schema.Str(row, left) == needleL && schema.Str(row, right) == needleR {
					n++
				}
			}
			if n > 1 {
				return &model.Reject{TxnID: txnID, Code: "UNIQUE_CONFLICT", Table: m.Table, PK: m.PK, Detail: model.UniqueKey(needleL, needleR)}
			}
		}
	}
	if rej := holdAggregate(txnID, state); rej != nil {
		return rej
	}
	return nil
}

func CommittedConsistent(visible []model.RowVersion) bool {
	state := Merge(visible, nil)
	if holdAggregate(0, state) != nil {
		return false
	}
	return stateInvariants(state) == nil
}

func stateInvariants(state map[string]map[string]any) *model.Reject {
	seenPK := map[string]bool{}
	uniqueSeen := map[string]string{}
	for key, row := range state {
		if row == nil {
			continue
		}
		table, pk := splitKey(key)
		if table == "" {
			continue
		}
		if seenPK[key] {
			return &model.Reject{Code: "PK_CONFLICT", Table: table, PK: pk, Detail: pk}
		}
		seenPK[key] = true
		if code, detail := qtyCheck(table, row); code != "" {
			return &model.Reject{Code: code, Table: table, PK: pk, Detail: detail}
		}
		if parentTable, field, ok := schema.ParentRef(table); ok {
			ppk := schema.Str(row, field)
			if ppk == "" || state[model.RowKey(parentTable, ppk)] == nil {
				return &model.Reject{Code: "FK_MISSING", Table: table, PK: pk, Detail: ppk}
			}
		}
		if left, right, ok := schema.UniqueSpec(table); ok {
			uk := table + "/" + model.UniqueKey(schema.Str(row, left), schema.Str(row, right))
			if prev, exists := uniqueSeen[uk]; exists && prev != pk {
				return &model.Reject{Code: "UNIQUE_CONFLICT", Table: table, PK: pk, Detail: uk}
			}
			uniqueSeen[uk] = pk
		}
		if table == model.TableTenant && !schema.ValidStatus(schema.Str(row, "status")) {
			return &model.Reject{Code: "CHECK_FAIL", Table: table, PK: pk, Detail: "status"}
		}
	}
	return nil
}

func splitKey(key string) (string, string) {
	for _, table := range model.Tables {
		prefix := table + "/"
		if len(key) > len(prefix) && key[:len(prefix)] == prefix {
			return table, key[len(prefix):]
		}
	}
	return "", ""
}

func opOK(op string) bool {
	return schema.ValidOp(op)
}

func hasPK(visible []model.RowVersion, table, pk string) bool {
	for _, v := range visible {
		if v.Table == table && v.PK == pk {
			return true
		}
	}
	return false
}

func frozenTenant(state map[string]map[string]any, m model.Mutation, payload map[string]any) *model.Reject {
	if m.Table != model.TableOffer && m.Table != model.TableHold {
		return nil
	}
	tenantID := schema.Str(payload, "tenant_id")
	t := state[model.RowKey(model.TableTenant, tenantID)]
	if t != nil && schema.Str(t, "status") == "FROZEN" {
		return &model.Reject{Code: "FROZEN_TENANT", Table: m.Table, PK: m.PK, Detail: tenantID}
	}
	return nil
}

func qtyCheck(table string, payload map[string]any) (string, string) {
	if table == model.TableOffer {
		qty, ok := schema.IntField(payload, "qty_on_hand")
		if !ok || qty < 0 {
			return "CHECK_FAIL", "qty_on_hand"
		}
	}
	if table == model.TableHold {
		qty, ok := schema.IntField(payload, "qty")
		if !ok || qty <= 0 {
			return "CHECK_FAIL", "qty"
		}
	}
	return "", ""
}

func holdAggregate(txnID int64, state map[string]map[string]any) *model.Reject {
	var holds []map[string]any
	for key, row := range state {
		if row != nil && len(key) >= 5 && key[:5] == "hold/" {
			holds = append(holds, row)
		}
	}
	for key, row := range state {
		if row == nil || len(key) < 6 || key[:6] != "offer/" {
			continue
		}
		if !holdqty.OK(row, holds) {
			return &model.Reject{TxnID: txnID, Code: "HOLD_QTY", Table: "offer", PK: key[6:], Detail: "qty"}
		}
	}
	return nil
}

func reject(txnID int64, code string, m model.Mutation, detail string) *model.Reject {
	return &model.Reject{TxnID: txnID, Code: code, Table: m.Table, PK: m.PK, Detail: detail}
}
