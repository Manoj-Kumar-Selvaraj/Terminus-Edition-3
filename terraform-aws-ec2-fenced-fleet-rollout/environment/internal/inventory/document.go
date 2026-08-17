package inventory

import (
	"sort"
	"strings"

	"fleetrollout/internal/types"
)

func InstanceIDs(instances []types.Value) []any {
	ids := make([]any, len(instances))
	for i, item := range instances {
		ids[i] = item["id"]
	}
	return ids
}

func VolumeIDs(volumes []types.Value) []any {
	ids := make([]any, len(volumes))
	for i, item := range volumes {
		ids[i] = item["id"]
	}
	return ids
}

func SubnetIDs(subnets []types.Value) []any {
	ids := make([]any, 0, len(subnets))
	for _, subnet := range subnets {
		ids = append(ids, subnet["id"])
	}
	return ids
}

func SortInstances(instances []types.Value) {
	sort.Slice(instances, func(i, j int) bool {
		return types.Int(instances[i]["slot"]) < types.Int(instances[j]["slot"])
	})
}

func ASG(config, refresh types.Value, desired int, subnetIDs []any) types.Value {
	asg := types.Object(config["asg"])
	return types.Value{
		"name":             types.Identifier("asg", config["app"], config["environment"]),
		"desired_capacity": desired,
		"min_size":         types.Int(asg["min_size"]),
		"max_size":         types.Int(asg["max_size"]),
		"subnet_ids":       subnetIDs,
		"instance_refresh": refresh,
	}
}

func Outputs(template, refresh types.Value, config types.Value, instanceIDs, volumeIDs, drift []any) types.Value {
	return types.Value{
		"launch_template_id":      template["id"],
		"launch_template_version": template["version"],
		"autoscaling_group_name":  types.Identifier("asg", config["app"], config["environment"]),
		"instance_ids":            instanceIDs,
		"volume_ids":              volumeIDs,
		"rollout_operation_id":    refresh["operation_id"],
		"drift_report":            drift,
	}
}

func Document(config, release, template, group, role, refresh, importReport types.Value, instances, volumes, driftReport []types.Value, actions []any, lost bool, subnetIDs []any) types.Value {
	desired := types.Int(types.Object(config["asg"])["desired_capacity"])
	SortInstances(instances)
	driftAny := types.AnyList(driftReport)
	result := types.Value{
		"schema_version":              types.StateSchema,
		"environment":                 config["environment"],
		"application":                 config["app"],
		"release_identity":            release,
		"launch_template":             template,
		"security_group":              group,
		"autoscaling_group":           ASG(config, refresh, desired, subnetIDs),
		"instances":                   types.AnyList(instances),
		"ebs_volumes":                 types.AnyList(volumes),
		"iam_role":                    role,
		"drift_report":                driftAny,
		"import_report":               importReport,
		"plan_actions":                actions,
		"journal_repair":              types.Value{"truncated_tail": false, "preserved_records": 0},
		"control_plane_response_lost": lost,
		"outputs":                     Outputs(template, refresh, config, InstanceIDs(instances), VolumeIDs(volumes), driftAny),
	}
	result["state_digest"] = types.Hash(result, 0)
	return result
}

func CollectStringIDs(state types.Value) []string {
	found := []string{}
	types.WalkStrings(state, func(value string) {
		if strings.HasPrefix(value, "i-") || strings.HasPrefix(value, "lt-") || strings.HasPrefix(value, "sg-") || strings.HasPrefix(value, "vol-") {
			found = append(found, value)
		}
	})
	sort.Strings(found)
	return types.UniqueStrings(found)
}
