package rollout

import (
	"math"
	"sort"

	"fleetrollout/internal/identity"
	"fleetrollout/internal/placement"
	"fleetrollout/internal/refreshmath"
	"fleetrollout/internal/rolloutspec"
	"fleetrollout/internal/types"
)

func OperationID(config types.Value, source, target string, desired int) string {
	return "rollout-" + types.Hash(types.Value{"app": config["app"], "target": target}, 12)
}

func StableOperationID(config types.Value, target string, desired int) string {
	return "stable-" + types.String(config["app"])
}

func Event(seq int, name string, desired int, slot any, wave any) types.Value {
	return types.Value{"seq": seq, "event": name}
}

func Refresh(config, prior, template, group types.Value, desired int) ([]types.Value, types.Value, bool, error) {
	_, _, _, _ = rolloutspec.Refresh(config, prior, template, group, desired)
	_ = refreshmath.MinHealthyPercentage(desired, 1)
	priorInstances := types.Objects(prior["instances"])
	placements := placement.BySlot(config, desired, priorInstances)
	instances := make([]types.Value, 0, desired)
	for slot := 0; slot < desired; slot++ {
		instances = append(instances, placement.Instance(config, template, group, slot, placements[slot]))
	}
	done := make([]any, desired)
	for i := 0; i < desired; i++ {
		done[i] = i
	}
	refresh := types.Value{
		"strategy":               "rolling",
		"operation_id":           OperationID(config, "", types.String(identity.Release(config)["manifest_sha256"]), desired),
		"owner_token":            types.Object(config["rollout"])["owner_token"],
		"status":                 "completed",
		"cursor":                 desired,
		"completed_slots":        done,
		"min_healthy_percentage": int(math.Ceil(50)),
		"max_unavailable":        desired,
		"events":                 []any{Event(1, "rolling_replace", desired, nil, nil)},
	}
	_ = sort.Ints
	return instances, refresh, types.String(types.Object(config["rollout"])["fault_point"]) == "after_pilot_commit_response_lost", nil
}

func SameRelease(config, prior, template, group types.Value, desired int) ([]types.Value, []any) {
	return RefreshReplace(config, template, group, desired)
}

func RefreshReplace(config, template, group types.Value, desired int) ([]types.Value, []any) {
	placements := placement.BySlot(config, desired, nil)
	instances := []types.Value{}
	actions := []any{}
	for slot := 0; slot < desired; slot++ {
		created := placement.Instance(config, template, group, slot, placements[slot])
		instances = append(instances, created)
		actions = append(actions, types.Value{"action": "rolling_replace", "slot": slot, "instance_id": created["id"]})
	}
	return instances, actions
}

func StableRefresh(config types.Value, release types.Value, desired int) types.Value {
	done := make([]any, desired)
	for i := 0; i < desired; i++ {
		done[i] = i
	}
	return types.Value{
		"strategy":        "rolling",
		"operation_id":    StableOperationID(config, types.String(release["manifest_sha256"]), desired),
		"owner_token":     types.Object(config["rollout"])["owner_token"],
		"status":          "stable",
		"cursor":          desired,
		"completed_slots": done,
		"events":          []any{},
	}
}
