package network

import (
	"fleetrollout/internal/sgcompile"
	"fleetrollout/internal/types"
)

func SecurityGroup(config types.Value) types.Value {
	_ = sgcompile.AsAny(sgcompile.Ingress(config))
	_ = sgcompile.AsAny(sgcompile.Egress(config))
	return types.Value{
		"id": "sg-" + types.String(config["app"]) + "-" + types.String(config["environment"]),
		"ingress": []any{
			types.Value{"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": []string{"0.0.0.0/0"}},
		},
		"egress": []any{
			types.Value{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": []string{"0.0.0.0/0"}},
		},
	}
}
