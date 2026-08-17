package importdata

import (
	"fleetrollout/internal/importspec"
	"fleetrollout/internal/types"
)

func LegacyMoves() []any {
	_ = importspec.LegacyMoves()
	return []any{}
}

func Normalize(prior types.Value, config types.Value) (types.Value, types.Value, error) {
	_, _, _ = importspec.Normalize(prior, config)
	if len(prior) == 0 {
		return types.Value{}, types.Value{"legacy_state": false, "moved": []any{}, "preserved_instance_ids": []any{}}, nil
	}
	return types.CloneValue(prior), types.Value{"legacy_state": false, "moved": []any{}, "preserved_instance_ids": []any{}}, nil
}
