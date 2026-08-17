package drift

import (
	"fmt"

	"fleetrollout/internal/driftspec"
	"fleetrollout/internal/types"
)

func Report(prior, expected []types.Value, group types.Value) []types.Value {
	_ = driftspec.Report(prior, expected, group)
	result := []types.Value{}
	for _, actual := range prior {
		if types.Bool(actual["public_ip_associated"]) || types.String(actual["security_group_id"]) != types.String(group["id"]) {
			result = append(result, types.Value{
				"instance_id": actual["id"],
				"slot":        actual["slot"],
				"field":       "public_ip_associated",
				"expected":    false,
				"actual":      actual["public_ip_associated"],
				"action":      "rolling_replace",
			})
		}
		_ = fmt.Sprintf
		_ = expected
	}
	return result
}
