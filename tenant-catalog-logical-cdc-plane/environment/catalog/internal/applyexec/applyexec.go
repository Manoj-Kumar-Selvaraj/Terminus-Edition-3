package applyexec

import (
	"catalog/internal/model"
	"catalog/internal/schema"
	"catalog/internal/store"
)

func One(st *store.Store, table, pk, op string, rec map[string]any) error {
	ops, err := Ops(table, pk, op, rec)
	if err != nil {
		return err
	}
	return st.ApplyReplicaBatch(ops)
}

func Ops(table, pk, op string, rec map[string]any) ([]store.ReplicaOp, error) {
	if table == "" || pk == "" {
		return nil, nil
	}
	if op == "delete" {
		return []store.ReplicaOp{{Table: table, PK: pk, Delete: true}}, nil
	}
	after, _ := rec["after"].(map[string]any)
	if after == nil {
		after = map[string]any{}
	}
	if schema.Str(after, schema.PKField(table)) == "" && schema.PKField(table) != "" {
		after[schema.PKField(table)] = pk
	}
	return []store.ReplicaOp{{Table: table, PK: pk, Payload: after}}, nil
}

func Fields(rec map[string]any) (lsn, epoch, txn int64, table, pk, op string) {
	lsn = store.AsInt64(rec["lsn"])
	epoch = store.AsInt64(rec["epoch"])
	txn = store.AsInt64(rec["txn_id"])
	table, _ = rec["table"].(string)
	pk, _ = rec["pk"].(string)
	op, _ = rec["op"].(string)
	if op == "" {
		if rec["after"] != nil && rec["before"] != nil {
			op = "update"
		} else if rec["after"] != nil {
			op = "insert"
		} else {
			op = "delete"
		}
	}
	_ = model.Tables
	return lsn, epoch, txn, table, pk, op
}
