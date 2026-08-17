package fence

import (
	"catalog/internal/model"
	"catalog/internal/store"
)

// Decision classifies one CDC record relative to the replica slot.
type Decision int

const (
	DecisionApply Decision = iota
	DecisionSkip
	DecisionRejectBatch
)

// Classify returns how a single record should be handled under LSN/epoch fencing.
func Classify(slot model.ReplicaSlot, epoch, lsn int64) Decision {
	if epoch != slot.Epoch {
		return DecisionRejectBatch
	}
	if lsn <= slot.ConfirmedLSN {
		return DecisionSkip
	}
	return DecisionApply
}

// BatchEpochOK is true when every record epoch matches the slot epoch.
func BatchEpochOK(slot model.ReplicaSlot, epochs []int64) bool {
	for _, e := range epochs {
		if e != slot.Epoch {
			return false
		}
	}
	return true
}

// ScanEpochs extracts epoch fields from CDC maps.
func ScanEpochs(records []map[string]any) []int64 {
	out := make([]int64, 0, len(records))
	for _, rec := range records {
		out = append(out, store.AsInt64(rec["epoch"]))
	}
	return out
}

// ScanLSNs extracts lsn fields from CDC maps.
func ScanLSNs(records []map[string]any) []int64 {
	out := make([]int64, 0, len(records))
	for _, rec := range records {
		out = append(out, store.AsInt64(rec["lsn"]))
	}
	return out
}

// MonotonicLSNs reports whether LSN values are non-decreasing in the given order.
func MonotonicLSNs(lsns []int64) bool {
	for i := 1; i < len(lsns); i++ {
		if lsns[i] < lsns[i-1] {
			return false
		}
	}
	return true
}

// AdvanceConfirmed returns the next confirmed_lsn after applying maxApplied,
// or the prior value when nothing was applied.
func AdvanceConfirmed(prior, maxApplied int64, appliedAny bool) int64 {
	if !appliedAny {
		return prior
	}
	if maxApplied > prior {
		return maxApplied
	}
	return prior
}

// RejectWholeBatch builds the apply counters when epoch fencing rejects the file.
func RejectWholeBatch(slot model.ReplicaSlot, n int) (applied, skipped, rejected int, confirmed int64) {
	return 0, 0, n, slot.ConfirmedLSN
}

// CountSkips counts records at or below confirmed_lsn.
func CountSkips(slot model.ReplicaSlot, lsns []int64) int {
	n := 0
	for _, lsn := range lsns {
		if lsn <= slot.ConfirmedLSN {
			n++
		}
	}
	return n
}

// FilterApplicable returns indexes of records that should apply under fencing.
func FilterApplicable(slot model.ReplicaSlot, records []map[string]any) []int {
	var idxs []int
	for i, rec := range records {
		epoch := store.AsInt64(rec["epoch"])
		lsn := store.AsInt64(rec["lsn"])
		if Classify(slot, epoch, lsn) == DecisionApply {
			idxs = append(idxs, i)
		}
	}
	return idxs
}

// FirstRejectReason returns a stable reason string for operator reports.
func FirstRejectReason(slot model.ReplicaSlot, records []map[string]any) string {
	for _, rec := range records {
		epoch := store.AsInt64(rec["epoch"])
		if epoch != slot.Epoch {
			return "epoch_mismatch"
		}
	}
	return ""
}

// SlotMatchesHealth is true when health epoch fields equal the durable slot.
func SlotMatchesHealth(slot model.ReplicaSlot, healthEpoch, healthReplicaEpoch int64) bool {
	return slot.Epoch == healthEpoch && slot.Epoch == healthReplicaEpoch
}

// ConfirmedNotPastDurable is the replica_ok LSN half of the health contract.
func ConfirmedNotPastDurable(confirmed, durable int64) bool {
	return confirmed <= durable
}
