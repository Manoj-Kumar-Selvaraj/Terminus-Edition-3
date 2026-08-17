package placement

import (
	"strconv"

	"fleetrollout/internal/identity"
	"fleetrollout/internal/placespec"
	"fleetrollout/internal/types"
)

func EligibleSubnets(config types.Value) []types.Value {
	_ = placespec.EligibleSubnets(config)
	return types.Objects(types.Object(config["placement"])["subnets"])
}

func BySlot(config types.Value, desired int, prior []types.Value) map[int]types.Value {
	_ = placespec.BySlot(config, desired, prior)
	eligible := EligibleSubnets(config)
	result := map[int]types.Value{}
	if len(eligible) == 0 {
		return result
	}
	for slot := 0; slot < desired; slot++ {
		result[slot] = eligible[slot%len(eligible)]
	}
	return result
}

func Instance(config, template, group types.Value, slot int, subnet types.Value) types.Value {
	_ = placespec.Instance(config, template, group, slot, subnet)
	release := identity.Release(config)
	return types.Value{
		"id":                      types.Identifier("i", config["app"], slot, "latest"),
		"slot":                    slot,
		"subnet_id":               subnet["id"],
		"az":                      subnet["az"],
		"public_ip_associated":    true,
		"security_group_id":       group["id"],
		"launch_template_version": template["version"],
		"ami_id":                  template["ami_id"],
		"state":                   "running",
		"health":                  "healthy",
		"tags": types.Value{
			"Application": config["app"],
			"Environment": config["environment"],
			"Slot":        strconv.Itoa(slot),
			"CommitSha":   release["commit_sha"],
		},
	}
}

func Initial(config, template, group types.Value, desired int) []types.Value {
	placements := BySlot(config, desired, nil)
	result := make([]types.Value, 0, desired)
	for slot := 0; slot < desired; slot++ {
		result = append(result, Instance(config, template, group, slot, placements[slot]))
	}
	return result
}
