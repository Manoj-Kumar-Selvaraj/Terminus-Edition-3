package replica

import (
	"catalog/internal/applyexec"
	"catalog/internal/applyorder"
	"catalog/internal/paths"
	"catalog/internal/store"
	"encoding/json"
	"os"
)

type Report struct {
	Applied      int   `json:"applied"`
	Skipped      int   `json:"skipped"`
	Rejected     int   `json:"rejected"`
	ConfirmedLSN int64 `json:"confirmed_lsn"`
	Epoch        int64 `json:"epoch"`
}

// Apply is the starter implementation: reverse FK order, ignore LSN/epoch fences.
func Apply(st *store.Store, records []map[string]any) (Report, error) {
	slot, err := st.LoadSlot()
	if err != nil {
		return Report{}, err
	}
	ordered := applyorder.Order(records, true)
	applied := 0
	maxLSN := slot.ConfirmedLSN
	var ops []store.ReplicaOp
	for _, rec := range ordered {
		lsn, _, _, table, pk, op := applyexec.Fields(rec)
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
