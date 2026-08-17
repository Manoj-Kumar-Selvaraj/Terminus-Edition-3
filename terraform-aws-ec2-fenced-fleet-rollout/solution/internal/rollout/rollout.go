package rollout

import (
	"fmt"
	"math"
	"sort"

	"fleetrollout/internal/fence"
	"fleetrollout/internal/identity"
	"fleetrollout/internal/placement"
	"fleetrollout/internal/types"
)

func OperationID(config types.Value, source, target string, desired int) string {
	return "rollout-" + types.Hash(types.Value{
		"app":              config["app"],
		"environment":      config["environment"],
		"source_manifest":  source,
		"target_manifest":  target,
		"desired_capacity": desired,
	}, 18)
}

func StableOperationID(config types.Value, target string, desired int) string {
	return "stable-" + types.Hash(types.Value{
		"app":              config["app"],
		"environment":      config["environment"],
		"target_manifest":  target,
		"desired_capacity": desired,
	}, 18)
}

func Event(seq int, name string, desired int, slot any, wave any) types.Value {
	result := types.Value{"seq": seq, "event": name, "healthy_capacity": desired, "unavailable": 0}
	if slot != nil {
		result["slot"] = slot
	}
	if wave != nil {
		result["wave"] = wave
	}
	return result
}

func makeRefresh(operation string, rollout types.Value, source, target string, desired, cursor int, status string, done []int, items []types.Value) types.Value {
	encoded := make([]any, len(done))
	for i, v := range done {
		encoded[i] = v
	}
	encodedEvents := make([]any, len(items))
	for i, v := range items {
		encodedEvents[i] = v
	}
	return types.Value{
		"strategy":                 types.PilotThenWave,
		"operation_id":             operation,
		"owner_token":              rollout["owner_token"],
		"source_manifest_sha256":   source,
		"target_manifest_sha256":   target,
		"status":                   status,
		"cursor":                   cursor,
		"completed_slots":          encoded,
		"min_healthy_percentage":   int(math.Ceil(float64((desired-1)*100) / float64(desired))),
		"max_unavailable":          1,
		"events":                   encodedEvents,
	}
}

func Refresh(config, prior, template, group types.Value, desired int) ([]types.Value, types.Value, bool, error) {
	priorInstances := types.Objects(prior["instances"])
	sort.Slice(priorInstances, func(i, j int) bool {
		return types.Int(priorInstances[i]["slot"]) < types.Int(priorInstances[j]["slot"])
	})
	targetManifest := types.String(identity.Release(config)["manifest_sha256"])
	priorRefresh := types.Object(types.Object(prior["autoscaling_group"])["instance_refresh"])
	inProgress := types.String(priorRefresh["status"]) == "in_progress"
	rolloutCfg := types.Object(config["rollout"])
	var source, operation string
	completed := []int{}
	events := []types.Value{}
	if inProgress {
		if err := fence.Guard(config, priorRefresh, targetManifest); err != nil {
			return nil, nil, false, err
		}
		source = types.String(priorRefresh["source_manifest_sha256"])
		operation = types.String(priorRefresh["operation_id"])
		for _, value := range anyList(priorRefresh["completed_slots"]) {
			completed = append(completed, types.Int(value))
		}
		events = types.Objects(priorRefresh["events"])
	} else {
		source = types.String(types.Object(prior["release_identity"])["manifest_sha256"])
		operation = OperationID(config, source, targetManifest, desired)
	}
	placements := placement.BySlot(config, desired, priorInstances)
	current := map[int]types.Value{}
	for _, item := range priorInstances {
		current[types.Int(item["slot"])] = item
	}
	target := map[int]types.Value{}
	for slot := 0; slot < desired; slot++ {
		target[slot] = placement.Instance(config, template, group, slot, placements[slot])
	}
	health, fault := types.String(rolloutCfg["candidate_health"]), types.String(rolloutCfg["fault_point"])
	if health == "" {
		health = "passing"
	}
	if fault == "" {
		fault = "none"
	}
	if !inProgress && health == "fail_pilot" {
		events = []types.Value{
			Event(1, "pilot_launched", desired, 0, nil),
			Event(2, "pilot_unhealthy", desired, 0, nil),
			Event(3, "previous_capacity_preserved", desired, nil, nil),
		}
		return priorInstances, makeRefresh(operation, rolloutCfg, source, targetManifest, desired, 0, "rolled_back", []int{}, events), false, nil
	}
	if !inProgress && health == "fail_wave" {
		launched := Event(4, "wave_launched", desired, nil, 1)
		unhealthy := Event(5, "wave_unhealthy", desired, nil, 1)
		firstWave := make([]any, 0, types.Int(types.Object(config["asg"])["wave_size"]))
		for slot := 1; slot < desired && len(firstWave) < types.Int(types.Object(config["asg"])["wave_size"]); slot++ {
			firstWave = append(firstWave, slot)
		}
		launched["slots"] = firstWave
		unhealthy["slots"] = types.Clone(firstWave)
		events = []types.Value{
			Event(1, "pilot_launched", desired, 0, nil),
			Event(2, "pilot_healthy", desired, 0, nil),
			Event(3, "pilot_committed", desired, 0, nil),
			launched,
			unhealthy,
			Event(6, "previous_capacity_preserved", desired, nil, nil),
		}
		return priorInstances, makeRefresh(operation, rolloutCfg, source, targetManifest, desired, 0, "rolled_back", []int{}, events), false, nil
	}
	sequence := 0
	for _, item := range events {
		if types.Int(item["seq"]) > sequence {
			sequence = types.Int(item["seq"])
		}
	}
	hasPilot := false
	for _, slot := range completed {
		if slot == 0 {
			hasPilot = true
		}
	}
	if !hasPilot {
		for _, name := range []string{"pilot_launched", "pilot_healthy", "pilot_committed"} {
			sequence++
			events = append(events, Event(sequence, name, desired, 0, nil))
		}
		current[0] = target[0]
		completed = append(completed, 0)
		if fault == "after_pilot_commit_response_lost" {
			mixed := []types.Value{}
			for slot := 0; slot < desired; slot++ {
				if item, ok := current[slot]; ok {
					mixed = append(mixed, item)
				}
			}
			return mixed, makeRefresh(operation, rolloutCfg, source, targetManifest, desired, 1, "in_progress", completed, events), true, nil
		}
	}
	remaining := []int{}
	completeSet := map[int]bool{}
	for _, slot := range completed {
		completeSet[slot] = true
	}
	for slot := 0; slot < desired; slot++ {
		if !completeSet[slot] {
			remaining = append(remaining, slot)
		}
	}
	waveSize := types.Int(types.Object(config["asg"])["wave_size"])
	if waveSize < 1 {
		return nil, nil, false, fmt.Errorf("asg.wave_size must be positive")
	}
	wave := 0
	for start := 0; start < len(remaining); start += waveSize {
		wave++
		end := start + waveSize
		if end > len(remaining) {
			end = len(remaining)
		}
		slots := remaining[start:end]
		for _, name := range []string{"wave_launched", "wave_healthy", "wave_committed"} {
			sequence++
			item := Event(sequence, name, desired, nil, wave)
			encoded := make([]any, len(slots))
			for i, slot := range slots {
				encoded[i] = slot
			}
			item["slots"] = encoded
			events = append(events, item)
		}
		for _, slot := range slots {
			current[slot] = target[slot]
			completed = append(completed, slot)
		}
	}
	sequence++
	events = append(events, Event(sequence, "rollout_completed", desired, nil, nil))
	instances := make([]types.Value, 0, desired)
	for slot := 0; slot < desired; slot++ {
		instances = append(instances, current[slot])
	}
	sort.Ints(completed)
	return instances, makeRefresh(operation, rolloutCfg, source, targetManifest, desired, desired, "completed", completed, events), false, nil
}

func SameRelease(config, prior, template, group types.Value, desired int) ([]types.Value, []any) {
	priorInstances := types.Objects(prior["instances"])
	sort.Slice(priorInstances, func(i, j int) bool {
		return types.Int(priorInstances[i]["slot"]) < types.Int(priorInstances[j]["slot"])
	})
	placements := placement.BySlot(config, desired, priorInstances)
	bySlot := map[int]types.Value{}
	for _, item := range priorInstances {
		bySlot[types.Int(item["slot"])] = item
	}
	instances := []types.Value{}
	actions := []any{}
	for slot := 0; slot < desired; slot++ {
		if item, ok := bySlot[slot]; ok {
			instances = append(instances, item)
			actions = append(actions, types.Value{"action": "no_op", "slot": slot, "instance_id": item["id"]})
		} else {
			created := placement.Instance(config, template, group, slot, placements[slot])
			instances = append(instances, created)
			actions = append(actions, types.Value{"action": "create", "slot": slot, "instance_id": created["id"]})
		}
	}
	for slot, item := range bySlot {
		if slot >= desired {
			actions = append(actions, types.Value{"action": "scale_in", "slot": slot, "instance_id": item["id"]})
		}
	}
	return instances, actions
}

func StableRefresh(config types.Value, release types.Value, desired int) types.Value {
	done := make([]any, desired)
	for i := 0; i < desired; i++ {
		done[i] = i
	}
	return types.Value{
		"strategy":               types.PilotThenWave,
		"operation_id":           StableOperationID(config, types.String(release["manifest_sha256"]), desired),
		"owner_token":            types.Object(config["rollout"])["owner_token"],
		"source_manifest_sha256": nil,
		"target_manifest_sha256": release["manifest_sha256"],
		"status":                 "stable",
		"cursor":                 desired,
		"completed_slots":        done,
		"min_healthy_percentage": int(math.Ceil(float64((desired-1)*100) / float64(desired))),
		"max_unavailable":        1,
		"events":                 []any{},
	}
}

func anyList(value any) []any {
	list, _ := value.([]any)
	return list
}
