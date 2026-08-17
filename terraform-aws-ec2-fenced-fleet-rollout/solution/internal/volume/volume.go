package volume

import (
	"fmt"
	"sort"

	"fleetrollout/internal/ebspolicy"
	"fleetrollout/internal/types"
)

func Attachments(config types.Value, instances []types.Value, prior types.Value) ([]types.Value, error) {
	priorInstances := map[string]int{}
	for _, item := range types.Objects(prior["instances"]) {
		priorInstances[types.String(item["id"])] = types.Int(item["slot"])
	}
	priorVolumes := map[string]types.Value{}
	for _, vol := range types.Objects(prior["ebs_volumes"]) {
		slot := types.Int(vol["slot"])
		attached := types.String(vol["attached_instance_id"])
		if actual, ok := priorInstances[attached]; attached != "" && ok && actual != slot {
			return nil, fmt.Errorf("volume %s violates slot ownership", types.String(vol["id"]))
		}
		priorVolumes[ebspolicy.SlotKey(slot, types.String(vol["logical_name"]))] = vol
	}
	result := []types.Value{}
	for _, item := range instances {
		slot := types.Int(item["slot"])
		for _, definition := range types.Objects(config["ebs_volumes"]) {
			name := types.String(definition["logical_name"])
			previous := priorVolumes[ebspolicy.SlotKey(slot, name)]
			result = append(result, ebspolicy.Record(config, item, definition, previous))
		}
	}
	sort.Slice(result, func(i, j int) bool {
		if types.Int(result[i]["slot"]) == types.Int(result[j]["slot"]) {
			return types.String(result[i]["logical_name"]) < types.String(result[j]["logical_name"])
		}
		return types.Int(result[i]["slot"]) < types.Int(result[j]["slot"])
	})
	return result, nil
}
