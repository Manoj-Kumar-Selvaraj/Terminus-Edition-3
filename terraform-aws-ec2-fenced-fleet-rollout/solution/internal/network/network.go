package network

import (
	"fleetrollout/internal/sgcompile"
	"fleetrollout/internal/types"
)

func SecurityGroup(config types.Value) types.Value {
	return types.Value{
		"id":      sgcompile.GroupID(config),
		"ingress": sgcompile.AsAny(sgcompile.Ingress(config)),
		"egress":  sgcompile.AsAny(sgcompile.Egress(config)),
	}
}
