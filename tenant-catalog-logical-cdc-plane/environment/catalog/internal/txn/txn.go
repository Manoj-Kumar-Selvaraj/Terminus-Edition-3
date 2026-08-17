package txn

import (
	"encoding/json"
	"fmt"
	"os"

	"catalog/internal/config"
	"catalog/internal/constraints"
	"catalog/internal/heap"
	"catalog/internal/indexes"
	"catalog/internal/jsonl"
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/schema"
	"catalog/internal/snapshot"
	"catalog/internal/store"
	"catalog/internal/wal"
)

func NextIDs(st *store.Store) (txnID, lsn int64, err error) {
	recs, err := st.LoadWAL()
	if err != nil {
		return 0, 0, err
	}
	txnID = wal.MaxTxn(recs)
	reg, err := st.MaxTxnID()
	if err != nil {
		return 0, 0, err
	}
	if reg > txnID {
		txnID = reg
	}
	lsn = wal.DurableLSN(recs)
	return txnID + 1, lsn + 1, nil
}

func Commit(st *store.Store, mutations []model.Mutation) (*model.Reject, error) {
	if len(mutations) == 0 {
		return nil, nil
	}
	cfg, err := config.Load()
	if err != nil {
		return nil, err
	}
	txnID, lsn, err := NextIDs(st)
	if err != nil {
		return nil, err
	}
	snap := txnID
	if err := st.AppendWAL(model.WalRecord{LSN: lsn, TxnID: txnID, Kind: "BEGIN", Epoch: cfg.ReplicaEpoch}); err != nil {
		return nil, err
	}
	lsn++
	writer := txnID
	visible, err := snapshot.Visible(st, snap, &writer)
	if err != nil {
		return nil, err
	}
	byKey := map[string]model.RowVersion{}
	for _, v := range visible {
		byKey[model.RowKey(v.Table, v.PK)] = v
	}
	for _, m := range mutations {
		before, after := beforeAfter(m.Op, m.Table, m.PK, m.Payload, byKey)
		overlayVisible(byKey, m)
		rec := model.WalRecord{
			LSN:    lsn,
			TxnID:  txnID,
			Kind:   model.OpKind(m.Op),
			Epoch:  cfg.ReplicaEpoch,
			Table:  m.Table,
			PK:     m.PK,
			Before: before,
			After:  after,
		}
		if err := st.AppendWAL(rec); err != nil {
			return nil, err
		}
		lsn++
	}
	rej, err := constraints.Check(st, snap, txnID, mutations)
	if err != nil {
		return nil, err
	}
	if rej != nil {
		if err := st.AppendWAL(model.WalRecord{LSN: lsn, TxnID: txnID, Kind: "ABORT", Epoch: cfg.ReplicaEpoch}); err != nil {
			return nil, err
		}
		if err := st.MarkAborted(txnID); err != nil {
			return nil, err
		}
		if err := jsonl.AppendJSON(paths.Rejects(), rej); err != nil {
			return nil, err
		}
		return rej, nil
	}
	if err := st.AppendWAL(model.WalRecord{LSN: lsn, TxnID: txnID, Kind: "COMMIT", Epoch: cfg.ReplicaEpoch}); err != nil {
		return nil, err
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return nil, err
	}
	if err := heap.Install(st, txnID, mutations, recs); err != nil {
		return nil, err
	}
	if err := indexes.Rebuild(st, snap); err != nil {
		return nil, err
	}
	return nil, nil
}

func LoadMutations(path string) ([]model.Mutation, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []model.Mutation
	for _, line := range splitLines(string(b)) {
		var m model.Mutation
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			return nil, err
		}
		if m.Payload == nil {
			m.Payload = map[string]any{}
		}
		if !schema.ValidOp(m.Op) {
			return nil, errInvalidMutation(m)
		}
		out = append(out, m)
	}
	return out, nil
}

func splitLines(s string) []string {
	var out []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			line := trim(s[start:i])
			if line != "" {
				out = append(out, line)
			}
			start = i + 1
		}
	}
	if start < len(s) {
		line := trim(s[start:])
		if line != "" {
			out = append(out, line)
		}
	}
	return out
}

func trim(s string) string {
	i, j := 0, len(s)
	for i < j && (s[i] == ' ' || s[i] == '\r' || s[i] == '\t') {
		i++
	}
	for j > i && (s[j-1] == ' ' || s[j-1] == '\r' || s[j-1] == '\t') {
		j--
	}
	return s[i:j]
}

func errInvalidMutation(m model.Mutation) error {
	return fmt.Errorf("invalid mutation op %q for %s/%s", m.Op, m.Table, m.PK)
}
