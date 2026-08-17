package driftspec

import (
	"fmt"

	"fleetrollout/internal/types"
)

func Report(prior, expected []types.Value, group types.Value) []types.Value {
	expectedBySlot := map[int]types.Value{}
	for _, item := range expected {
		expectedBySlot[types.Int(item["slot"])] = item
	}
	result := []types.Value{}
	for _, actual := range prior {
		slot := types.Int(actual["slot"])
		wanted, ok := expectedBySlot[slot]
		if !ok {
			continue
		}
		checks := []struct {
			field    string
			expected any
		}{
			{"launch_template_version", wanted["launch_template_version"]},
			{"public_ip_associated", false},
			{"subnet_id", wanted["subnet_id"]},
			{"security_group_id", group["id"]},
		}
		for _, check := range checks {
			if fmt.Sprint(actual[check.field]) != fmt.Sprint(check.expected) {
				result = append(result, types.Value{
					"instance_id": actual["id"],
					"slot":        slot,
					"field":       check.field,
					"expected":    check.expected,
					"actual":      actual[check.field],
					"action":      "report_only",
				})
			}
		}
	}
	return result
}
