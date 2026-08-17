package walvalidate

import (
	"fmt"
	"sort"

	"catalog/internal/model"
)

// Summary captures structural facts about a durable WAL stream.
type Summary struct {
	RecordCount     int
	DurableLSN      int64
	MaxTxnID        int64
	CommittedTxns   int
	AbortedTxns     int
	OpenTxns        []int64
	Gaps            []int64
	DuplicateLSNs  []int64
	EpochSet        map[int64]struct{}
	OrphanMutations int
	BeginWithoutEnd int
}

// Summarize walks WAL records and reports continuity / txn pairing issues.
func Summarize(records []model.WalRecord) Summary {
	sum := Summary{EpochSet: map[int64]struct{}{}}
	seenLSN := map[int64]int{}
	begun := map[int64]bool{}
	ended := map[int64]string{}
	mutCount := map[int64]int{}

	for _, r := range records {
		sum.RecordCount++
		if r.LSN > sum.DurableLSN {
			sum.DurableLSN = r.LSN
		}
		if r.TxnID > sum.MaxTxnID {
			sum.MaxTxnID = r.TxnID
		}
		sum.EpochSet[r.Epoch] = struct{}{}
		seenLSN[r.LSN]++
		switch r.Kind {
		case "BEGIN":
			begun[r.TxnID] = true
		case "COMMIT":
			ended[r.TxnID] = "COMMIT"
			sum.CommittedTxns++
		case "ABORT":
			ended[r.TxnID] = "ABORT"
			sum.AbortedTxns++
		case "INSERT", "UPDATE", "DELETE":
			mutCount[r.TxnID]++
			if !begun[r.TxnID] && ended[r.TxnID] == "" {
				sum.OrphanMutations++
			}
		}
	}

	for lsn, n := range seenLSN {
		if n > 1 {
			sum.DuplicateLSNs = append(sum.DuplicateLSNs, lsn)
		}
	}
	sort.Slice(sum.DuplicateLSNs, func(i, j int) bool { return sum.DuplicateLSNs[i] < sum.DuplicateLSNs[j] })

	var present []int64
	for lsn := range seenLSN {
		present = append(present, lsn)
	}
	sort.Slice(present, func(i, j int) bool { return present[i] < present[j] })
	for i := 1; i < len(present); i++ {
		if present[i] != present[i-1]+1 {
			for g := present[i-1] + 1; g < present[i]; g++ {
				sum.Gaps = append(sum.Gaps, g)
			}
		}
	}

	for txnID := range begun {
		if ended[txnID] == "" {
			sum.OpenTxns = append(sum.OpenTxns, txnID)
			sum.BeginWithoutEnd++
		}
	}
	sort.Slice(sum.OpenTxns, func(i, j int) bool { return sum.OpenTxns[i] < sum.OpenTxns[j] })
	return sum
}

// ContiguousLSNs reports whether LSN values form a dense sequence from the first observed LSN.
func ContiguousLSNs(records []model.WalRecord) bool {
	sum := Summarize(records)
	return len(sum.Gaps) == 0 && len(sum.DuplicateLSNs) == 0
}

// OpenTxnIDs returns txn ids that have BEGIN without COMMIT/ABORT.
func OpenTxnIDs(records []model.WalRecord) []int64 {
	return Summarize(records).OpenTxns
}

// HasAbort reports whether txnID has a durable ABORT record.
func HasAbort(records []model.WalRecord, txnID int64) bool {
	for _, r := range records {
		if r.TxnID == txnID && r.Kind == "ABORT" {
			return true
		}
	}
	return false
}

// CommittedMutationLSNs lists LSNs of mutations belonging to committed txns, in order.
func CommittedMutationLSNs(records []model.WalRecord) []int64 {
	committed := map[int64]struct{}{}
	for _, r := range records {
		if r.Kind == "COMMIT" {
			committed[r.TxnID] = struct{}{}
		}
	}
	var out []int64
	for _, r := range records {
		if _, ok := committed[r.TxnID]; !ok {
			continue
		}
		if r.Kind == "INSERT" || r.Kind == "UPDATE" || r.Kind == "DELETE" {
			out = append(out, r.LSN)
		}
	}
	return out
}

// EpochAgreement checks that every record either shares expectedEpoch or is empty stream.
func EpochAgreement(records []model.WalRecord, expectedEpoch int64) bool {
	if len(records) == 0 {
		return true
	}
	for _, r := range records {
		if r.Epoch != expectedEpoch {
			return false
		}
	}
	return true
}

// RedoWindow returns mutation records with lsn > checkpointLSN belonging to committed txns.
func RedoWindow(records []model.WalRecord, checkpointLSN int64) []model.WalRecord {
	committed := map[int64]struct{}{}
	for _, r := range records {
		if r.Kind == "COMMIT" {
			committed[r.TxnID] = struct{}{}
		}
	}
	var out []model.WalRecord
	for _, r := range records {
		if r.LSN <= checkpointLSN {
			continue
		}
		if _, ok := committed[r.TxnID]; !ok {
			continue
		}
		if r.Kind == "INSERT" || r.Kind == "UPDATE" || r.Kind == "DELETE" {
			out = append(out, r)
		}
	}
	return out
}

// DescribeOpen formats open txn ids for operator diagnostics.
func DescribeOpen(records []model.WalRecord) string {
	open := OpenTxnIDs(records)
	if len(open) == 0 {
		return "none"
	}
	return fmt.Sprintf("%v", open)
}

// PairingOK is true when every BEGIN has exactly one terminal COMMIT or ABORT
// and no mutation exists without a BEGIN for that txn.
func PairingOK(records []model.WalRecord) bool {
	sum := Summarize(records)
	return sum.BeginWithoutEnd == 0 && sum.OrphanMutations == 0 && len(sum.DuplicateLSNs) == 0
}
