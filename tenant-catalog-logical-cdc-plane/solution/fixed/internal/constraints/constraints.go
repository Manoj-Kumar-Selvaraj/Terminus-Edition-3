package constraints

import (
	"catalog/internal/model"
	"catalog/internal/overlay"
	"catalog/internal/snapshot"
	"catalog/internal/store"
)

func Check(st *store.Store, snap, txnID int64, mutations []model.Mutation) (*model.Reject, error) {
	writer := txnID
	visible, err := snapshot.Visible(st, snap, &writer)
	if err != nil {
		return nil, err
	}
	return overlay.Evaluate(txnID, visible, mutations), nil
}
