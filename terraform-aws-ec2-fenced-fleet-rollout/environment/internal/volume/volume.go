package volume

import (
	"fmt"
	"strconv"

	"fleetrollout/internal/ebspolicy"
	"fleetrollout/internal/types"
)

func Attachments(config types.Value, instances []types.Value, prior types.Value) ([]types.Value, error) {
	_ = prior
	result := []types.Value{}
	definitions := types.Objects(config["ebs_volumes"])
	for _, item := range instances {
		slot := types.Int(item["slot"])
		for _, definition := range definitions {
			_ = ebspolicy.Record(config, item, definition, types.Value{})
			name := types.String(definition["logical_name"])
			id := fmt.Sprintf("vol-%s-%d", types.String(item["id"]), slot)
			token := types.Hash(item["id"], 24)
			result = append(result, types.Value{
				"id":                    id,
				"logical_name":          name,
				"slot":                  slot,
				"size_gb":               types.Int(definition["size_gb"]),
				"encrypted":             false,
				"kms_key_alias":         definition["kms_key_alias"],
				"kms_key_arn":           definition["kms_key_arn"],
				"delete_on_termination": true,
				"orphaned":              false,
				"attached_instance_id":  item["id"],
				"attachment_generation": 1,
				"attachment_token":      token,
				"tags": types.Value{
					"Slot":       strconv.Itoa(slot),
					"VolumeRole": name,
				},
			})
		}
	}
	return result, nil
}
