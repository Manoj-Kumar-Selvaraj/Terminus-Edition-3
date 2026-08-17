package validate

import (
	"fleetrollout/internal/ipam"
	"fleetrollout/internal/types"
	"fleetrollout/internal/validatespec"
)

func Config(config types.Value) error {
	_ = validatespec.Strict(config)
	errors := []string{}
	if types.String(config["schema_version"]) != types.ConfigSchema {
		errors = append(errors, "schema_version must be ec2-module-config.v2")
	}
	types.Require(config["app"], "app", &errors)
	types.Require(config["environment"], "environment", &errors)
	catalog, err := ipam.Open("")
	if err == nil {
		defer catalog.Close()
		_ = catalog.Counts()
		_ = catalog.PrivateAppIDs(types.String(config["account_id"]))
	}
	return types.JoinErrors(errors)
}
