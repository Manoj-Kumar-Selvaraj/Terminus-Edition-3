package store

import (
	"database/sql"
	"encoding/json"
	"os"
	"strings"

	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/schema"

	_ "modernc.org/sqlite"
)

const engineSchema = `
CREATE TABLE IF NOT EXISTS row_version (
    table_name TEXT NOT NULL,
    pk TEXT NOT NULL,
    xmin INTEGER NOT NULL,
    xmax INTEGER,
    committed INTEGER NOT NULL,
    lsn INTEGER NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS row_version_pk ON row_version (table_name, pk, xmin);
CREATE TABLE IF NOT EXISTS txn_reg (
    txn_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tenant_meta (
    tenant_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    plan TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sku_meta (
    sku_id TEXT PRIMARY KEY,
    category TEXT NOT NULL
);
`

type Store struct{}

func New() *Store { return &Store{} }

func (s *Store) openEngine() (*sql.DB, error) {
	if err := paths.EnsureDirs(); err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", paths.EngineDB())
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(engineSchema); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func (s *Store) OpenReplica() (*sql.DB, error) {
	if err := paths.EnsureDirs(); err != nil {
		return nil, err
	}
	schema, err := os.ReadFile(paths.SQLReplica())
	if err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", paths.ReplicaDB())
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(`PRAGMA foreign_keys = ON`); err != nil {
		db.Close()
		return nil, err
	}
	if _, err := db.Exec(string(schema)); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func (s *Store) LoadVersions() ([]model.RowVersion, error) {
	db, err := s.openEngine()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query(`SELECT table_name, pk, xmin, xmax, committed, lsn, payload FROM row_version`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []model.RowVersion
	for rows.Next() {
		var v model.RowVersion
		var xmax sql.NullInt64
		var committed int
		var payload string
		if err := rows.Scan(&v.Table, &v.PK, &v.Xmin, &xmax, &committed, &v.LSN, &payload); err != nil {
			return nil, err
		}
		if xmax.Valid {
			x := xmax.Int64
			v.Xmax = &x
		}
		v.Committed = committed != 0
		if err := json.Unmarshal([]byte(payload), &v.Payload); err != nil {
			v.Payload = map[string]any{}
		}
		out = append(out, v)
	}
	return out, rows.Err()
}

func (s *Store) ReplaceVersions(versions []model.RowVersion) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	if _, err := tx.Exec(`DELETE FROM row_version`); err != nil {
		tx.Rollback()
		return err
	}
	stmt, err := tx.Prepare(`INSERT INTO row_version(table_name, pk, xmin, xmax, committed, lsn, payload) VALUES (?, ?, ?, ?, ?, ?, ?)`)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer stmt.Close()
	for _, v := range versions {
		var xmax any
		if v.Xmax != nil {
			xmax = *v.Xmax
		}
		c := 0
		if v.Committed {
			c = 1
		}
		if _, err := stmt.Exec(v.Table, v.PK, v.Xmin, xmax, c, v.LSN, model.MustJSON(v.Payload)); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func (s *Store) UpsertVersion(v model.RowVersion) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	c := 0
	if v.Committed {
		c = 1
	}
	var xmax any
	if v.Xmax != nil {
		xmax = *v.Xmax
	}
	_, err = db.Exec(
		`INSERT INTO row_version(table_name, pk, xmin, xmax, committed, lsn, payload) VALUES (?, ?, ?, ?, ?, ?, ?)`,
		v.Table, v.PK, v.Xmin, xmax, c, v.LSN, model.MustJSON(v.Payload),
	)
	return err
}

func (s *Store) SetXmax(table, pk string, xmin, xmax int64) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(
		`UPDATE row_version SET xmax = ? WHERE table_name = ? AND pk = ? AND xmin = ? AND xmax IS NULL`,
		xmax, table, pk, xmin,
	)
	return err
}

func (s *Store) MarkCommitted(txnID int64) error {
	if txnID <= 0 {
		return nil
	}
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.Exec(`UPDATE row_version SET committed = 1 WHERE xmin = ? OR xmax = ?`, txnID, txnID); err != nil {
		return err
	}
	_, err = db.Exec(
		`INSERT INTO txn_reg(txn_id, state) VALUES (?, 'COMMITTED') ON CONFLICT(txn_id) DO UPDATE SET state = excluded.state`,
		txnID,
	)
	return err
}

func (s *Store) MarkAborted(txnID int64) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.Exec(`DELETE FROM row_version WHERE xmin = ? AND committed = 0`, txnID); err != nil {
		return err
	}
	if _, err := db.Exec(`UPDATE row_version SET xmax = NULL WHERE xmax = ? AND committed = 0`, txnID); err != nil {
		return err
	}
	_, err = db.Exec(
		`INSERT INTO txn_reg(txn_id, state) VALUES (?, 'ABORTED') ON CONFLICT(txn_id) DO UPDATE SET state = excluded.state`,
		txnID,
	)
	return err
}

func (s *Store) MaxTxnID() (int64, error) {
	db, err := s.openEngine()
	if err != nil {
		return 0, err
	}
	defer db.Close()
	var n sql.NullInt64
	if err := db.QueryRow(`SELECT MAX(txn_id) FROM txn_reg`).Scan(&n); err != nil {
		return 0, err
	}
	if n.Valid {
		return n.Int64, nil
	}
	return 0, nil
}

func (s *Store) LoadWAL() ([]model.WalRecord, error) {
	b, err := os.ReadFile(paths.WAL())
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var out []model.WalRecord
	for _, line := range strings.Split(string(b), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var rec model.WalRecord
		if err := json.Unmarshal([]byte(line), &rec); err != nil {
			return nil, err
		}
		out = append(out, rec)
	}
	return out, nil
}

func (s *Store) AppendWAL(rec model.WalRecord) error {
	if err := paths.EnsureDirs(); err != nil {
		return err
	}
	f, err := os.OpenFile(paths.WAL(), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	b, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	_, err = f.Write(append(b, '\n'))
	return err
}

func (s *Store) DurableLSN() (int64, error) {
	recs, err := s.LoadWAL()
	if err != nil {
		return 0, err
	}
	var max int64
	for _, r := range recs {
		if r.LSN > max {
			max = r.LSN
		}
	}
	return max, nil
}

func (s *Store) LoadCheckpoint() (map[string]any, error) {
	b, err := os.ReadFile(paths.Checkpoint())
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]any{"lsn": 0.0, "txn_id": 0.0, "epoch": 1.0, "heap": []any{}}, nil
		}
		return nil, err
	}
	var doc map[string]any
	if err := json.Unmarshal(b, &doc); err != nil {
		return nil, err
	}
	return doc, nil
}

func (s *Store) WriteCheckpoint(doc any) error {
	b, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(paths.Checkpoint(), append(b, '\n'), 0o644)
}

func (s *Store) LoadIndexes() (map[string]map[string]string, error) {
	out := map[string]map[string]string{"sku_code": {}, "offer_code": {}}
	b, err := os.ReadFile(paths.Indexes())
	if err != nil {
		if os.IsNotExist(err) {
			return out, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(b, &out); err != nil {
		return nil, err
	}
	if out["sku_code"] == nil {
		out["sku_code"] = map[string]string{}
	}
	if out["offer_code"] == nil {
		out["offer_code"] = map[string]string{}
	}
	return out, nil
}

func (s *Store) WriteIndexes(idx map[string]map[string]string) error {
	b, err := json.MarshalIndent(idx, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(paths.Indexes(), append(b, '\n'), 0o644)
}

func (s *Store) LoadSlot() (model.ReplicaSlot, error) {
	b, err := os.ReadFile(paths.ReplicaSlot())
	if err != nil {
		if os.IsNotExist(err) {
			return model.ReplicaSlot{Epoch: 1}, nil
		}
		return model.ReplicaSlot{}, err
	}
	var slot model.ReplicaSlot
	if err := json.Unmarshal(b, &slot); err != nil {
		return model.ReplicaSlot{}, err
	}
	return slot, nil
}

func (s *Store) WriteSlot(slot model.ReplicaSlot) error {
	b, err := json.MarshalIndent(slot, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(paths.ReplicaSlot(), append(b, '\n'), 0o644)
}

func (s *Store) ReplicaRows(table string) ([]map[string]any, error) {
	db, err := s.OpenReplica()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query(`SELECT * FROM ` + table)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	var out []map[string]any
	for rows.Next() {
		vals := make([]any, len(cols))
		ptrs := make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		row := map[string]any{}
		for i, c := range cols {
			switch v := vals[i].(type) {
			case []byte:
				row[c] = string(v)
			default:
				row[c] = v
			}
		}
		out = append(out, row)
	}
	return out, rows.Err()
}

func (s *Store) ReplicaUpsert(table, pk string, payload map[string]any) error {
	db, err := s.OpenReplica()
	if err != nil {
		return err
	}
	defer db.Close()
	return s.replicaUpsertDB(db, table, pk, payload)
}

func (s *Store) ReplicaDelete(table, pk string) error {
	db, err := s.OpenReplica()
	if err != nil {
		return err
	}
	defer db.Close()
	return s.replicaDeleteDB(db, table, pk)
}

func (s *Store) ApplyReplicaBatch(ops []ReplicaOp) error {
	if len(ops) == 0 {
		return nil
	}
	db, err := s.OpenReplica()
	if err != nil {
		return err
	}
	defer db.Close()
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	for _, op := range ops {
		if op.Delete {
			if _, err := tx.Exec(`DELETE FROM `+op.Table+` WHERE `+op.Table+`_id = ?`, op.PK); err != nil {
				tx.Rollback()
				return err
			}
			continue
		}
		if err := s.replicaUpsertTx(tx, op.Table, op.PK, op.Payload); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

type ReplicaOp struct {
	Table   string
	PK      string
	Delete  bool
	Payload map[string]any
}

func (s *Store) replicaDeleteDB(db *sql.DB, table, pk string) error {
	_, err := db.Exec(`DELETE FROM `+table+` WHERE `+table+`_id = ?`, pk)
	return err
}

func (s *Store) replicaUpsertDB(db *sql.DB, table, pk string, payload map[string]any) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	if err := s.replicaUpsertTx(tx, table, pk, payload); err != nil {
		tx.Rollback()
		return err
	}
	return tx.Commit()
}

func (s *Store) replicaUpsertTx(tx *sql.Tx, table, pk string, payload map[string]any) error {
	var err error
	switch table {
	case model.TableTenant:
		_, err = tx.Exec(
			`INSERT INTO tenant(tenant_id, status) VALUES (?, ?) ON CONFLICT(tenant_id) DO UPDATE SET status = excluded.status`,
			pk, schema.Str(payload, "status"),
		)
	case model.TableSKU:
		_, err = tx.Exec(
			`INSERT INTO sku(sku_id, tenant_id, sku_code) VALUES (?, ?, ?) ON CONFLICT(sku_id) DO UPDATE SET tenant_id = excluded.tenant_id, sku_code = excluded.sku_code`,
			pk, schema.Str(payload, "tenant_id"), schema.Str(payload, "sku_code"),
		)
	case model.TableOffer:
		qty, _ := schema.IntField(payload, "qty_on_hand")
		_, err = tx.Exec(
			`INSERT INTO offer(offer_id, tenant_id, sku_id, offer_code, qty_on_hand) VALUES (?, ?, ?, ?, ?) ON CONFLICT(offer_id) DO UPDATE SET tenant_id = excluded.tenant_id, sku_id = excluded.sku_id, offer_code = excluded.offer_code, qty_on_hand = excluded.qty_on_hand`,
			pk, schema.Str(payload, "tenant_id"), schema.Str(payload, "sku_id"), schema.Str(payload, "offer_code"), qty,
		)
	case model.TableHold:
		qty, _ := schema.IntField(payload, "qty")
		_, err = tx.Exec(
			`INSERT INTO hold(hold_id, tenant_id, offer_id, qty) VALUES (?, ?, ?, ?) ON CONFLICT(hold_id) DO UPDATE SET tenant_id = excluded.tenant_id, offer_id = excluded.offer_id, qty = excluded.qty`,
			pk, schema.Str(payload, "tenant_id"), schema.Str(payload, "offer_id"), qty,
		)
	}
	return err
}

func (s *Store) ReplaceWAL(recs []model.WalRecord) error {
	if err := paths.EnsureDirs(); err != nil {
		return err
	}
	f, err := os.Create(paths.WAL())
	if err != nil {
		return err
	}
	defer f.Close()
	for _, rec := range recs {
		b, err := json.Marshal(rec)
		if err != nil {
			return err
		}
		if _, err := f.Write(append(b, '\n')); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) InsertTenantMeta(tenantID, region, plan string) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`INSERT INTO tenant_meta(tenant_id, region, plan) VALUES (?, ?, ?) ON CONFLICT(tenant_id) DO UPDATE SET region = excluded.region, plan = excluded.plan`, tenantID, region, plan)
	return err
}

func (s *Store) InsertSKUMeta(skuID, category string) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`INSERT INTO sku_meta(sku_id, category) VALUES (?, ?) ON CONFLICT(sku_id) DO UPDATE SET category = excluded.category`, skuID, category)
	return err
}

func (s *Store) EnsureEngineMeta() error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`
CREATE TABLE IF NOT EXISTS tenant_meta (
    tenant_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    plan TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sku_meta (
    sku_id TEXT PRIMARY KEY,
    category TEXT NOT NULL
);`)
	return err
}

func (s *Store) RegisterCommitted(ids []int64) error {
	db, err := s.openEngine()
	if err != nil {
		return err
	}
	defer db.Close()
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	stmt, err := tx.Prepare(`INSERT INTO txn_reg(txn_id, state) VALUES (?, 'COMMITTED') ON CONFLICT(txn_id) DO UPDATE SET state = excluded.state`)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer stmt.Close()
	for _, id := range ids {
		if _, err := stmt.Exec(id); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func AsInt64(v any) int64 {
	switch n := v.(type) {
	case float64:
		return int64(n)
	case int64:
		return n
	case int:
		return int64(n)
	case json.Number:
		i, _ := n.Int64()
		return i
	default:
		return 0
	}
}
