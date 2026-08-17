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

func AbortedTxns(records []model.WalRecord) map[int64]struct{} {
	aborted := map[int64]struct{}{}
	for _, r := range records {
		if r.Kind == "ABORT" {
			aborted[r.TxnID] = struct{}{}
		}
	}
	return aborted
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

func HasAbort(records []model.WalRecord, txnID int64) bool {
	_, ok := AbortedTxns(records)[txnID]
	return ok
}

func RecordsAfter(records []model.WalRecord, lsn int64) []model.WalRecord {
	var out []model.WalRecord
	for _, r := range records {
		if r.LSN > lsn {
			out = append(out, r)
		}
	}
	return out
}

func FilterByTxn(records []model.WalRecord, txnID int64) []model.WalRecord {
	var out []model.WalRecord
	for _, r := range records {
		if r.TxnID == txnID {
			out = append(out, r)
		}
	}
	return out
}

func KindCounts(records []model.WalRecord) map[string]int {
	out := map[string]int{}
	for _, r := range records {
		out[r.Kind]++
	}
	return out
}

func TerminalKind(records []model.WalRecord, txnID int64) string {
	kind := ""
	for _, r := range records {
		if r.TxnID != txnID {
			continue
		}
		if r.Kind == "COMMIT" || r.Kind == "ABORT" {
			kind = r.Kind
		}
	}
	return kind
}

func MutationOp(kind string) string {
	switch kind {
	case "INSERT":
		return "insert"
	case "UPDATE":
		return "update"
	case "DELETE":
		return "delete"
	default:
		return ""
	}
}
