package engine

import (
	"os"

	"catalog/internal/cdc"
	"catalog/internal/checkpoint"
	"catalog/internal/config"
	"catalog/internal/health"
	"catalog/internal/inspect"
	"catalog/internal/jsonl"
	"catalog/internal/paths"
	"catalog/internal/recover"
	"catalog/internal/replica"
	"catalog/internal/snapshot"
	"catalog/internal/store"
	"catalog/internal/txn"
	"catalog/internal/visibility"
	"catalog/internal/wal"
)

func Commit(st *store.Store, input string) error {
	mutations, err := txn.LoadMutations(input)
	if err != nil {
		return err
	}
	if _, err := txn.Commit(st, mutations); err != nil {
		return err
	}
	return health.Write(st)
}

func Decode(st *store.Store) error {
	slot, err := st.LoadSlot()
	if err != nil {
		return err
	}
	events, err := cdc.Decode(st, slot.ConfirmedLSN)
	if err != nil {
		return err
	}
	if err := cdc.Write(events); err != nil {
		return err
	}
	return health.Write(st)
}

func Apply(st *store.Store, cdcPath string) error {
	if cdcPath == "" {
		cdcPath = paths.CDC()
	}
	records, err := jsonl.ReadMaps(cdcPath)
	if err != nil {
		if os.IsNotExist(err) {
			records = nil
		} else {
			return err
		}
	}
	if _, err := replica.Apply(st, records); err != nil {
		return err
	}
	return health.Write(st)
}

func Recover(st *store.Store) error {
	if err := recover.Recover(st); err != nil {
		return err
	}
	return health.Write(st)
}

func Checkpoint(st *store.Store) error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	recs, err := st.LoadWAL()
	if err != nil {
		return err
	}
	committed := wal.CommittedTxns(recs)
	var latest int64
	for id := range committed {
		if id > latest {
			latest = id
		}
	}
	versions, err := st.LoadVersions()
	if err != nil {
		return err
	}
	visible := visibility.SnapshotVisible(versions, latest, nil, committed)
	slot, err := st.LoadSlot()
	if err != nil {
		return err
	}
	_ = cfg
	_ = snapshot.Visible
	doc := checkpoint.FromVersions(wal.DurableLSN(recs), latest, slot.Epoch, visible)
	if err := checkpoint.Write(doc); err != nil {
		return err
	}
	return health.Write(st)
}

func Inspect(st *store.Store) error {
	return inspect.Inspect(st)
}

func EmptyCheck(st *store.Store) error {
	return inspect.EmptyCheck(st)
}
