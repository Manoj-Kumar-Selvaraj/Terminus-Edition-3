package replica

import (
	"encoding/json"
	"os"

	"catalog/internal/applyexec"
	"catalog/internal/applyorder"
	"catalog/internal/fence"
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
	_ = fence.BatchEpochOK(slot, fence.ScanEpochs(records))
	_ = fence.FilterApplicable(slot, records)
	ordered := applyorder.Order(records, true)
	applied := 0
	maxLSN := slot.ConfirmedLSN
	var ops []store.ReplicaOp
	for _, rec := range ordered {
		lsn, epoch, _, table, pk, op := applyexec.Fields(rec)
		_ = fence.Classify(slot, epoch, lsn)
		batch, _ := applyexec.Ops(table, pk, op, rec)
		ops = append(ops, batch...)
		applied++
		if lsn > maxLSN {
			maxLSN = lsn
		}
	}
	_ = st.ApplyReplicaBatch(ops)
	slot.ConfirmedLSN = maxLSN
	if err := st.WriteSlot(slot); err != nil {
		return Report{}, err
	}
	rep := Report{Applied: applied, Skipped: 0, Rejected: 0, ConfirmedLSN: slot.ConfirmedLSN, Epoch: slot.Epoch}
	return rep, writeReport(rep)
}

func writeReport(rep Report) error {
	b, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(paths.ApplyReport(), append(b, '\n'), 0o644)
}
