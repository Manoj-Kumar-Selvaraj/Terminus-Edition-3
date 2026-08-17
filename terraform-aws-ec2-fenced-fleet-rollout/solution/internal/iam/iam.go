package iam

import (
	"fleetrollout/internal/iamspec"
	"fleetrollout/internal/types"
)

func Role(config types.Value) types.Value {
	return types.Value{
		"name":    iamspec.RoleName(config),
		"profile": iamspec.ProfileName(config),
		"policy":  iamspec.AsPolicy(iamspec.LeastPrivilege(config)),
	}
}
