package ebspolicy

import (
	"fmt"
	"strconv"

	"fleetrollout/internal/types"
)

func StableID(app string, slot int, name string) string {
	return types.Identifier("vol", app, slot, name)
}

func Token(volumeID, instanceID string, generation int) string {
	return types.Hash(types.Value{
		"generation":  generation,
		"instance_id": instanceID,
		"volume_id":   volumeID,
	}, 24)
}

func NextGeneration(previous types.Value, instanceID string) int {
	if len(previous) == 0 {
		return 1
	}
	if types.String(previous["attached_instance_id"]) != instanceID {
		return types.Int(previous["attachment_generation"]) + 1
	}
	return types.Int(previous["attachment_generation"])
}

func Record(config types.Value, instance types.Value, definition types.Value, previous types.Value) types.Value {
	slot := types.Int(instance["slot"])
	name := types.String(definition["logical_name"])
	stable := StableID(types.String(config["app"]), slot, name)
	generation := NextGeneration(previous, types.String(instance["id"]))
	return types.Value{
		"id":                    stable,
		"logical_name":          name,
		"slot":                  slot,
		"size_gb":               types.Int(definition["size_gb"]),
		"encrypted":             true,
		"kms_key_alias":         definition["kms_key_alias"],
		"kms_key_arn":           definition["kms_key_arn"],
		"delete_on_termination": false,
		"orphaned":              false,
		"attached_instance_id":  instance["id"],
		"attachment_generation": generation,
		"attachment_token":      Token(stable, types.String(instance["id"]), generation),
		"tags": types.Value{
			"Application": config["app"],
			"Environment": config["environment"],
			"Slot":        strconv.Itoa(slot),
			"VolumeRole":  name,
			"ManagedBy":   "terraform-aws-ec2-module",
		},
	}
}

func SlotKey(slot int, name string) string {
	return fmt.Sprintf("%d:%s", slot, name)
}
