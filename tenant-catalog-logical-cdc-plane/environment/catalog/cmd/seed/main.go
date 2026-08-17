package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	"catalog/internal/checkpoint"
	"catalog/internal/config"
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/schema"
	"catalog/internal/store"
	"catalog/internal/visibility"
	"catalog/internal/wal"

	_ "modernc.org/sqlite"
)

const (
	nTenants      = 40
	skusPerTenant = 20
	offersPerSKU  = 8
	nOfferUpdates = 1560
	epoch         = 3
)

var (
	regions    = []string{"us-east", "us-west", "eu-west", "ap-south"}
	plans      = []string{"standard", "enterprise", "starter"}
	categories = []string{"parts", "kits", "tools", "media", "spare"}
)

type seeder struct {
	st       *store.Store
	recs     []model.WalRecord
	versions []model.RowVersion
	txnIDs   []int64
	lsn      int64
	txn      int64
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	if err := paths.EnsureDirs(); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Join(paths.Root(), "warehouse"), 0o755); err != nil {
		return err
	}
	st := store.New()
	s := &seeder{st: st}
	if err := s.phaseTenantsAndSKUs(); err != nil {
		return err
	}
	skuEnd := s.lsn
	if err := s.phaseOffersAndHolds(); err != nil {
		return err
	}
	if err := s.phaseOfferHistory(); err != nil {
		return err
	}
	if err := st.ReplaceWAL(s.recs); err != nil {
		return err
	}
	if err := st.ReplaceVersions(s.versions); err != nil {
		return err
	}
	if err := st.RegisterCommitted(s.txnIDs); err != nil {
		return err
	}
	if err := writeIndexes(st, s.versions, s.recs); err != nil {
		return err
	}
	if err := writeCheckpoint(st, s.versions, s.recs, skuEnd); err != nil {
		return err
	}
	if err := st.WriteSlot(model.ReplicaSlot{Epoch: epoch, ConfirmedLSN: skuEnd}); err != nil {
		return err
	}
	if err := s.crashPending(); err != nil {
		return err
	}
	if err := writeWarehouse(st); err != nil {
		return err
	}
	return verifySeed(st)
}

func verifySeed(st *store.Store) error {
	versions, err := st.LoadVersions()
	if err != nil {
		return err
	}
	if len(versions) != 12001 {
		return fmt.Errorf("seed row_version count %d want 12001 including crash", len(versions))
	}
	var committed, crash int
	for _, v := range versions {
		if v.Committed {
			committed++
		}
		if v.PK == "s-crash-pending" {
			crash++
		}
	}
	if committed != 12000 {
		return fmt.Errorf("seed committed versions %d want 12000", committed)
	}
	if crash != 1 {
		return fmt.Errorf("seed missing crash pending sku")
	}
	slot, err := st.LoadSlot()
	if err != nil {
		return err
	}
	if slot.Epoch != epoch || slot.ConfirmedLSN <= 0 {
		return fmt.Errorf("seed replica slot epoch=%d lsn=%d", slot.Epoch, slot.ConfirmedLSN)
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return err
	}
	if wal.DurableLSN(recs) < slot.ConfirmedLSN {
		return fmt.Errorf("seed wal shorter than replica slot")
	}
	if wal.HasCommit(recs, 1) == false {
		return fmt.Errorf("seed missing first commit")
	}
	return nil
}

func (s *seeder) phaseTenantsAndSKUs() error {
	for t := 0; t < nTenants; t++ {
		tid := fmt.Sprintf("t%02d", t)
		status := "ACTIVE"
		if t%4 == 3 {
			status = "FROZEN"
		}
		payload := map[string]any{"tenant_id": tid, "status": status}
		s.commitInsert(model.TableTenant, tid, payload)
		if err := s.st.InsertTenantMeta(tid, regions[t%len(regions)], plans[t%len(plans)]); err != nil {
			return err
		}
		if err := s.st.ReplicaUpsert(model.TableTenant, tid, payload); err != nil {
			return err
		}
		for k := 0; k < skusPerTenant; k++ {
			sid := fmt.Sprintf("s-%s-%02d", tid, k)
			code := fmt.Sprintf("SKU%02d%02d", t, k)
			sp := map[string]any{"sku_id": sid, "tenant_id": tid, "sku_code": code}
			s.commitInsert(model.TableSKU, sid, sp)
			if err := s.st.InsertSKUMeta(sid, categories[(t*skusPerTenant+k)%len(categories)]); err != nil {
				return err
			}
			if err := s.st.ReplicaUpsert(model.TableSKU, sid, sp); err != nil {
				return err
			}
		}
	}
	return nil
}

func (s *seeder) phaseOffersAndHolds() error {
	offerN := 0
	for t := 0; t < nTenants; t++ {
		tid := fmt.Sprintf("t%02d", t)
		for k := 0; k < skusPerTenant; k++ {
			sid := fmt.Sprintf("s-%s-%02d", tid, k)
			for o := 0; o < offersPerSKU; o++ {
				oid := fmt.Sprintf("o-%s-%d", sid, o)
				code := fmt.Sprintf("OFF%02d%02d%d", t, k, o)
				qty := int64(10 + (offerN % 7))
				op := map[string]any{
					"offer_id": oid, "tenant_id": tid, "sku_id": sid,
					"offer_code": code, "qty_on_hand": qty,
				}
				s.commitInsert(model.TableOffer, oid, op)
				if o%2 == 0 {
					hid := "h-" + oid
					hq := []int64{1, 3, 2}[(o/2)%3]
					hp := map[string]any{"hold_id": hid, "tenant_id": tid, "offer_id": oid, "qty": hq}
					s.commitInsert(model.TableHold, hid, hp)
				}
				offerN++
			}
		}
	}
	return nil
}

func (s *seeder) phaseOfferHistory() error {
	type offerRef struct {
		oid     string
		xmin    int64
		payload map[string]any
	}
	var live []offerRef
	for _, v := range s.versions {
		if v.Table == model.TableOffer && v.Xmax == nil {
			live = append(live, offerRef{oid: v.PK, xmin: v.Xmin, payload: model.CopyMap(v.Payload)})
		}
	}
	n := nOfferUpdates
	if n > len(live) {
		n = len(live)
	}
	for i := 0; i < n; i++ {
		ref := live[i]
		qty, _ := schema.IntField(ref.payload, "qty_on_hand")
		after := model.CopyMap(ref.payload)
		after["qty_on_hand"] = qty + 1
		s.commitUpdate(model.TableOffer, ref.oid, ref.xmin, ref.payload, after)
	}
	return nil
}

func (s *seeder) commitInsert(table, pk string, payload map[string]any) {
	s.txn++
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{LSN: s.lsn, TxnID: s.txn, Kind: "BEGIN", Epoch: epoch})
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{
		LSN: s.lsn, TxnID: s.txn, Kind: "INSERT", Epoch: epoch,
		Table: table, PK: pk, Before: nil, After: model.CopyMap(payload),
	})
	mutLSN := s.lsn
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{LSN: s.lsn, TxnID: s.txn, Kind: "COMMIT", Epoch: epoch})
	s.versions = append(s.versions, model.RowVersion{
		Table: table, PK: pk, Xmin: s.txn, Committed: true, LSN: mutLSN, Payload: model.CopyMap(payload),
	})
	s.txnIDs = append(s.txnIDs, s.txn)
}

func (s *seeder) commitUpdate(table, pk string, prevXmin int64, before, after map[string]any) {
	s.txn++
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{LSN: s.lsn, TxnID: s.txn, Kind: "BEGIN", Epoch: epoch})
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{
		LSN: s.lsn, TxnID: s.txn, Kind: "UPDATE", Epoch: epoch,
		Table: table, PK: pk, Before: model.CopyMap(before), After: model.CopyMap(after),
	})
	mutLSN := s.lsn
	s.lsn++
	s.recs = append(s.recs, model.WalRecord{LSN: s.lsn, TxnID: s.txn, Kind: "COMMIT", Epoch: epoch})
	xmax := s.txn
	for i := range s.versions {
		v := &s.versions[i]
		if v.Table == table && v.PK == pk && v.Xmin == prevXmin && v.Xmax == nil {
			v.Xmax = &xmax
			break
		}
	}
	s.versions = append(s.versions, model.RowVersion{
		Table: table, PK: pk, Xmin: s.txn, Committed: true, LSN: mutLSN, Payload: model.CopyMap(after),
	})
	s.txnIDs = append(s.txnIDs, s.txn)
}

func (s *seeder) crashPending() error {
	s.txn++
	s.lsn++
	crash := []model.WalRecord{
		{LSN: s.lsn, TxnID: s.txn, Kind: "BEGIN", Epoch: epoch},
	}
	s.lsn++
	payload := map[string]any{"sku_id": "s-crash-pending", "tenant_id": "t00", "sku_code": "CRASH"}
	crash = append(crash, model.WalRecord{
		LSN: s.lsn, TxnID: s.txn, Kind: "INSERT", Epoch: epoch,
		Table: model.TableSKU, PK: "s-crash-pending", After: payload,
	})
	s.recs = append(s.recs, crash...)
	if err := s.st.ReplaceWAL(s.recs); err != nil {
		return err
	}
	v := model.RowVersion{
		Table: model.TableSKU, PK: "s-crash-pending", Xmin: s.txn, Committed: false, LSN: s.lsn, Payload: payload,
	}
	return s.st.UpsertVersion(v)
}

func writeIndexes(st *store.Store, versions []model.RowVersion, recs []model.WalRecord) error {
	committed := wal.CommittedTxns(recs)
	var latest int64
	for id := range committed {
		if id > latest {
			latest = id
		}
	}
	rows := visibility.SnapshotVisible(versions, latest, nil, committed)
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
	return st.WriteIndexes(idx)
}

func writeCheckpoint(st *store.Store, versions []model.RowVersion, recs []model.WalRecord, _ int64) error {
	committed := wal.CommittedTxns(recs)
	var latest int64
	for id := range committed {
		if id > latest {
			latest = id
		}
	}
	rows := visibility.SnapshotVisible(versions, latest, nil, committed)
	slot, err := st.LoadSlot()
	if err != nil {
		slot = model.ReplicaSlot{Epoch: epoch}
	}
	_ = config.Load
	doc := checkpoint.FromVersions(wal.DurableLSN(recs), latest, slot.Epoch, rows)
	if slot.Epoch == 0 {
		doc.Epoch = epoch
	}
	doc.Epoch = epoch
	return checkpoint.Write(doc)
}

func writeWarehouse(st *store.Store) error {
	_ = st
	path := paths.Warehouse()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.Exec(`
CREATE TABLE IF NOT EXISTS inventory (
    sku_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    on_hand INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS warehouse_bin (
    bin_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    qty INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS warehouse_note (
    note_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    body TEXT NOT NULL
);`); err != nil {
		return err
	}
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	inv, err := tx.Prepare(`INSERT INTO inventory(sku_id, tenant_id, on_hand) VALUES (?, ?, ?)`)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer inv.Close()
	bin, err := tx.Prepare(`INSERT INTO warehouse_bin(bin_id, region, sku_id, qty) VALUES (?, ?, ?, ?)`)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer bin.Close()
	note, err := tx.Prepare(`INSERT INTO warehouse_note(note_id, tenant_id, body) VALUES (?, ?, ?)`)
	if err != nil {
		tx.Rollback()
		return err
	}
	defer note.Close()
	n := 0
	for t := 0; t < nTenants; t++ {
		tid := fmt.Sprintf("t%02d", t)
		if _, err := note.Exec(t+1, tid, fmt.Sprintf("cycle dump for %s", tid)); err != nil {
			tx.Rollback()
			return err
		}
		for k := 0; k < skusPerTenant; k++ {
			sid := fmt.Sprintf("s-%s-%02d", tid, k)
			onHand := 10 + ((t*skusPerTenant + k) % 17)
			if _, err := inv.Exec(sid, tid, onHand); err != nil {
				tx.Rollback()
				return err
			}
			binID := fmt.Sprintf("bin-%s-%02d", tid, k)
			if _, err := bin.Exec(binID, regions[t%len(regions)], sid, onHand%9+1); err != nil {
				tx.Rollback()
				return err
			}
			n++
		}
	}
	if n == 0 {
		tx.Rollback()
		return fmt.Errorf("warehouse seed empty")
	}
	return tx.Commit()
}
