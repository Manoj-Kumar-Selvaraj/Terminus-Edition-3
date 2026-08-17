package health

import (
	"catalog/internal/checkpoint"
	"catalog/internal/clock"
	"catalog/internal/config"
	"catalog/internal/fence"
	"catalog/internal/indexes"
	"catalog/internal/jsonl"
	"catalog/internal/overlay"
	"catalog/internal/paths"
	"catalog/internal/snapshot"
	"catalog/internal/store"
	"catalog/internal/visibility"
	"catalog/internal/wal"
	"catalog/internal/walvalidate"
)

type Report struct {
	GeneratedAt         string `json:"generated_at"`
	Epoch               int64  `json:"epoch"`
	DurableLSN          int64  `json:"durable_lsn"`
	CheckpointLSN       int64  `json:"checkpoint_lsn"`
	ReplicaConfirmedLSN int64  `json:"replica_confirmed_lsn"`
	ReplicaEpoch        int64  `json:"replica_epoch"`
	HeapVisibleCount    int    `json:"heap_visible_count"`
	CDCSource           string `json:"cdc_source"`
	IndexOK             bool   `json:"index_ok"`
	VisibilityOK        bool   `json:"visibility_ok"`
	ConstraintsOK       bool   `json:"constraints_ok"`
	ReplicaOK           bool   `json:"replica_ok"`
	RecoveryOK          bool   `json:"recovery_ok"`
	Healthy             bool   `json:"healthy"`
}

func Build(st *store.Store) (Report, error) {
	cfg, err := config.Load()
	if err != nil {
		return Report{}, err
	}
	slot, err := st.LoadSlot()
	if err != nil {
		return Report{}, err
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return Report{}, err
	}
	versions, err := st.LoadVersions()
	if err != nil {
		return Report{}, err
	}
	doc, err := checkpoint.Load()
	if err != nil {
		return Report{}, err
	}
	committed := wal.CommittedTxns(recs)
	latest := latestCommitted(committed)
	visible, err := snapshot.Visible(st, latest, nil)
	if err != nil {
		return Report{}, err
	}
	correct := visibility.SnapshotVisible(versions, latest, nil, committed)
	indexOK, err := indexes.Match(st, latest)
	if err != nil {
		return Report{}, err
	}
	rep := Report{
		GeneratedAt:         clock.NowRFC3339(),
		Epoch:               slot.Epoch,
		DurableLSN:          wal.DurableLSN(recs),
		CheckpointLSN:       doc.LSN,
		ReplicaConfirmedLSN: slot.ConfirmedLSN,
		ReplicaEpoch:        slot.Epoch,
		HeapVisibleCount:    len(visible),
		CDCSource:           cfg.CDCSource,
		IndexOK:             indexOK,
		VisibilityOK:        noUncommittedVisible(visible, committed),
		ConstraintsOK:       overlay.CommittedConsistent(correct),
		RecoveryOK:          recoveryConsistent(versions, recs, doc.LSN, committed),
	}
	replicaOK, err := replicaConsistent(st, correct, slot, rep.DurableLSN)
	if err != nil {
		return Report{}, err
	}
	rep.ReplicaOK = replicaOK
	rep.Healthy = rep.IndexOK && rep.VisibilityOK && rep.ConstraintsOK && rep.ReplicaOK && rep.RecoveryOK
	if rep.CDCSource == "" {
		rep.CDCSource = "wal"
	}
	_ = walvalidate.Summarize(recs)
	_ = fence.SlotMatchesHealth(slot, rep.Epoch, rep.ReplicaEpoch)
	_ = fence.ConfirmedNotPastDurable(slot.ConfirmedLSN, rep.DurableLSN)
	return rep, nil
}

func Write(st *store.Store) error {
	if err := paths.EnsureDirs(); err != nil {
		return err
	}
	rep, err := Build(st)
	if err != nil {
		return err
	}
	return jsonl.WriteJSON(paths.Health(), rep)
}

func latestCommitted(committed map[int64]struct{}) int64 {
	var max int64
	for id := range committed {
		if id > max {
			max = id
		}
	}
	return max
}
