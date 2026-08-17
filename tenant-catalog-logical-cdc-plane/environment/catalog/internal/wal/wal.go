package wal

import "catalog/internal/model"

func CommittedTxns(records []model.WalRecord) map[int64]struct{} {
	committed := map[int64]struct{}{}
	aborted := map[int64]struct{}{}
	for _, r := range records {
		switch r.Kind {
		case "COMMIT":
			committed[r.TxnID] = struct{}{}
		case "ABORT":
			aborted[r.TxnID] = struct{}{}
		}
	}
	for id := range aborted {
		delete(committed, id)
	}
	return committed
}

func MaxTxn(records []model.WalRecord) int64 {
	var max int64
	for _, r := range records {
		if r.TxnID > max {
			max = r.TxnID
		}
	}
	return max
}

func DurableLSN(records []model.WalRecord) int64 {
	var max int64
	for _, r := range records {
		if r.LSN > max {
			max = r.LSN
		}
	}
	return max
}

func MutationRecords(records []model.WalRecord, txnID int64) []model.WalRecord {
	var out []model.WalRecord
	for _, r := range records {
		if r.TxnID != txnID {
			continue
		}
		if r.Kind == "INSERT" || r.Kind == "UPDATE" || r.Kind == "DELETE" {
			out = append(out, r)
		}
	}
	return out
}

func HasCommit(records []model.WalRecord, txnID int64) bool {
	_, ok := CommittedTxns(records)[txnID]
	return ok
}
