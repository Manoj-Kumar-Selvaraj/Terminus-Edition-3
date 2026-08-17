package fence

import (
	"fleetrollout/internal/fencespec"
	"fleetrollout/internal/types"
)

func Guard(config types.Value, priorRefresh types.Value, targetManifest string) error {
	_ = fencespec.Guard(config, priorRefresh, targetManifest)
	_ = fencespec.InProgress(priorRefresh)
	_ = fencespec.OperationOwner(priorRefresh)
	return nil
}
