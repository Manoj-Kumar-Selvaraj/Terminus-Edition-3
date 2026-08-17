package fencespec

import (
	"fmt"

	"fleetrollout/internal/types"
)

func Guard(config types.Value, priorRefresh types.Value, targetManifest string) error {
	if len(priorRefresh) == 0 {
		return nil
	}
	if types.String(priorRefresh["status"]) != "in_progress" {
		return nil
	}
	if types.String(priorRefresh["target_manifest_sha256"]) != targetManifest {
		return fmt.Errorf("target release changed during in-progress rollout")
	}
	owner := types.Object(config["rollout"])["owner_token"]
	if priorRefresh["owner_token"] != owner {
		return fmt.Errorf("stale rollout owner cannot resume in-progress operation")
	}
	return nil
}

func InProgress(refresh types.Value) bool {
	return types.String(refresh["status"]) == "in_progress"
}

func OperationOwner(refresh types.Value) string {
	return types.String(refresh["owner_token"])
}
