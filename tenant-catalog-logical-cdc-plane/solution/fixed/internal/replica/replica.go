package replica

import (
	"encoding/json"
	"os"

	"catalog/internal/applyexec"
	"catalog/internal/applyorder"
	"catalog/internal/fence"
	"catalog/internal/model"
	"catalog/internal/paths"
	"catalog/internal/store"
)

type Report struct {
	Applied      int   `json:"applied"`
	Skipped      int   `json:"skipped"`
	Rejected     int   `json:"rejected"`
	ConfirmedLSN int64 `json:"confirmed_lsn"`
	Epoch        int64 `json:"epoch"`
}

func Apply(st *store.Store, records []map[string]any) (Report, error) {
	slot, err := st.LoadSlot()
	if err != nil {
		return Report{}, err
	}
	rep := Report{Epoch: slot.Epoch, ConfirmedLSN: slot.ConfirmedLSN}
	if len(records) == 0 {
		return rep, writeReport(rep)
	}
	if !fence.BatchEpochOK(slot, fence.ScanEpochs(records)) {
		rep.Applied, rep.Skipped, rep.Rejected, rep.ConfirmedLSN = fence.RejectWholeBatch(slot, len(records))
		return rep, writeReport(rep)
	}
	ordered := applyorder.Order(records, false)
	var maxApplied int64
	appliedAny := false
	var ops []store.ReplicaOp
	for _, rec := range ordered {
		lsn, epoch, _, table, pk, op := applyexec.Fields(rec)
		switch fence.Classify(slot, epoch, lsn) {
		case fence.DecisionRejectBatch:
			rep.Applied, rep.Skipped, rep.Rejected, rep.ConfirmedLSN = fence.RejectWholeBatch(slot, len(records))
			return rep, writeReport(rep)
		case fence.DecisionSkip:
			rep.Skipped++
			continue
		}
		batch, err := applyexec.Ops(table, pk, op, rec)
		if err != nil {
			return Report{}, err
		}
		ops = append(ops, batch...)
		rep.Applied++
		appliedAny = true
		if lsn > maxApplied {
			maxApplied = lsn
		}
	}
	if err := st.ApplyReplicaBatch(ops); err != nil {
		return Report{}, err
	}
	slot.ConfirmedLSN = fence.AdvanceConfirmed(slot.ConfirmedLSN, maxApplied, appliedAny)
	if appliedAny {
		if err := st.WriteSlot(slot); err != nil {
			return Report{}, err
		}
	}
	rep.ConfirmedLSN = slot.ConfirmedLSN
	rep.Epoch = slot.Epoch
	_ = model.Tables
	return rep, writeReport(rep)
}

func writeReport(rep Report) error {
	b, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(paths.ApplyReport(), append(b, '\n'), 0o644)
}
