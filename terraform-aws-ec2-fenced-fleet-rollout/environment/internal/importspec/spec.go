package importspec

import (
	"fmt"
	"sort"
	"strconv"

	"fleetrollout/internal/identity"
	"fleetrollout/internal/types"
)

func LegacyMoves() []any {
	return []any{
		types.Value{"from": "aws_launch_template.payments", "to": "aws_launch_template.this"},
		types.Value{"from": "aws_autoscaling_group.payments", "to": "aws_autoscaling_group.this"},
		types.Value{"from": "aws_security_group.payments_instance", "to": "aws_security_group.instance"},
		types.Value{"from": "aws_iam_role.payments_instance", "to": "aws_iam_role.instance"},
		types.Value{"from": "aws_ebs_volume.payments_data", "to": "aws_ebs_volume.data"},
		types.Value{"from": "aws_volume_attachment.payments_data", "to": "aws_volume_attachment.data"},
	}
}

func Normalize(prior types.Value, config types.Value) (types.Value, types.Value, error) {
	if len(prior) == 0 {
		return types.Value{}, types.Value{"legacy_state": false, "moved": []any{}, "preserved_instance_ids": []any{}}, nil
	}
	normalized := types.CloneValue(prior)
	legacy := types.String(normalized["schema_version"]) != types.StateSchema
	instances := types.Objects(normalized["instances"])
	for _, instance := range instances {
		if _, exists := instance["slot"]; !exists {
			raw, found := types.Object(instance["tags"])["Slot"]
			if !found {
				return nil, nil, fmt.Errorf("legacy instance %s is missing Slot tag", types.String(instance["id"]))
			}
			parsed, err := strconv.Atoi(types.String(raw))
			if err != nil {
				return nil, nil, fmt.Errorf("legacy instance %s has invalid Slot tag", types.String(instance["id"]))
			}
			instance["slot"] = parsed
		}
	}
	sort.Slice(instances, func(i, j int) bool {
		return types.Int(instances[i]["slot"]) < types.Int(instances[j]["slot"])
	})
	normalizedInstances := make([]any, len(instances))
	preserved := make([]any, len(instances))
	for i, instance := range instances {
		normalizedInstances[i], preserved[i] = instance, instance["id"]
	}
	normalized["instances"] = normalizedInstances
	if _, exists := normalized["release_identity"]; !exists {
		normalized["release_identity"] = identity.Release(config)
	}
	moved := []any{}
	if legacy {
		moved = LegacyMoves()
	}
	return normalized, types.Value{"legacy_state": legacy, "moved": moved, "preserved_instance_ids": preserved}, nil
}
