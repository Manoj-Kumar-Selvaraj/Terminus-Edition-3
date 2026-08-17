package replica

import (
	"encoding/json"
	"os"

	"catalog/internal/applyexec"
	"catalog/internal/applyorder"
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
	for _, rec := range records {
		if store.AsInt64(rec["epoch"]) != slot.Epoch {
			rep.Rejected = len(records)
			return rep, writeReport(rep)
		}
	}
	ordered := applyorder.Order(records, false)
	var maxApplied int64
	appliedAny := false
	var ops []store.ReplicaOp
	for _, rec := range ordered {
		lsn, _, _, table, pk, op := applyexec.Fields(rec)
		if lsn <= slot.ConfirmedLSN {
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
	if appliedAny {
		slot.ConfirmedLSN = maxApplied
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
