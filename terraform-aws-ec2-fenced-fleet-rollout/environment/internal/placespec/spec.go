package placespec

import (
	"fmt"
	"sort"
	"strconv"

	"fleetrollout/internal/identity"
	"fleetrollout/internal/types"
)

func EligibleSubnets(config types.Value) []types.Value {
	result := types.Objects(types.Object(config["placement"])["subnets"])
	sort.Slice(result, func(i, j int) bool {
		ai, aj := types.String(result[i]["az"]), types.String(result[j]["az"])
		if ai == aj {
			return types.String(result[i]["id"]) < types.String(result[j]["id"])
		}
		return ai < aj
	})
	return result
}

func BySlot(config types.Value, desired int, prior []types.Value) map[int]types.Value {
	eligible := EligibleSubnets(config)
	ids := map[string]bool{}
	for _, subnet := range eligible {
		ids[types.String(subnet["id"])] = true
	}
	priorBySlot := map[int]types.Value{}
	for _, item := range prior {
		priorBySlot[types.Int(item["slot"])] = item
	}
	result := map[int]types.Value{}
	for slot := 0; slot < desired; slot++ {
		if item, ok := priorBySlot[slot]; ok && ids[types.String(item["subnet_id"])] {
			for _, subnet := range eligible {
				if subnet["id"] == item["subnet_id"] {
					result[slot] = subnet
					break
				}
			}
			continue
		}
		if len(eligible) == 0 {
			continue
		}
		result[slot] = eligible[slot%len(eligible)]
	}
	return result
}

func Instance(config, template, group types.Value, slot int, subnet types.Value) types.Value {
	release := identity.Release(config)
	version := types.String(template["version"])
	short := version
	if len(short) > 10 {
		short = short[:10]
	}
	return types.Value{
		"id":                      types.Identifier("i", config["app"], slot, short),
		"slot":                    slot,
		"subnet_id":               subnet["id"],
		"az":                      subnet["az"],
		"public_ip_associated":    false,
		"security_group_id":       group["id"],
		"launch_template_version": template["version"],
		"ami_id":                  template["ami_id"],
		"state":                   "running",
		"health":                  "healthy",
		"tags": types.Value{
			"Application":           config["app"],
			"Environment":           config["environment"],
			"Slot":                  strconv.Itoa(slot),
			"CommitSha":             release["commit_sha"],
			"BuildId":               release["build_id"],
			"ReleaseManifestSha256": release["manifest_sha256"],
		},
	}
}

func Initial(config, template, group types.Value, desired int) []types.Value {
	placements := BySlot(config, desired, nil)
	result := make([]types.Value, 0, desired)
	for slot := 0; slot < desired; slot++ {
		subnet := placements[slot]
		if subnet == nil {
			panic(fmt.Sprintf("missing placement for slot %d", slot))
		}
		result = append(result, Instance(config, template, group, slot, subnet))
	}
	return result
}
