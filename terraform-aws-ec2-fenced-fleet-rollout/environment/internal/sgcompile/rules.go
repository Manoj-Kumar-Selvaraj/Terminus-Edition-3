package sgcompile

import (
	"fleetrollout/internal/types"
)

type Rule struct {
	Protocol string
	FromPort int
	ToPort   int
	SourceSG string
	CIDRs    []string
	Prefixes []string
}

func (r Rule) AsValue() types.Value {
	result := types.Value{
		"protocol":  r.Protocol,
		"from_port": r.FromPort,
		"to_port":   r.ToPort,
	}
	if r.SourceSG != "" {
		result["source_security_group_id"] = r.SourceSG
	}
	if len(r.CIDRs) > 0 {
		result["cidr_blocks"] = r.CIDRs
	}
	if len(r.Prefixes) > 0 {
		result["prefix_list_ids"] = r.Prefixes
	}
	return result
}

func IsOpenWorldSSH(rule Rule) bool {
	if rule.FromPort != 22 || rule.ToPort != 22 {
		return false
	}
	for _, cidr := range rule.CIDRs {
		if cidr == "0.0.0.0/0" || cidr == "::/0" {
			return true
		}
	}
	return false
}

func Ingress(config types.Value) []Rule {
	net := types.Object(config["network"])
	port := types.Int(config["service_port"])
	return []Rule{{
		Protocol: "tcp",
		FromPort: port,
		ToPort:   port,
		SourceSG: types.String(net["alb_security_group_id"]),
	}}
}

func Egress(config types.Value) []Rule {
	net := types.Object(config["network"])
	prefixes := types.SortedCopy(types.StringList(net["endpoint_prefix_lists"]))
	resolver := types.String(net["resolver_security_group_id"])
	return []Rule{
		{Protocol: "tcp", FromPort: 443, ToPort: 443, Prefixes: prefixes},
		{Protocol: "udp", FromPort: 53, ToPort: 53, SourceSG: resolver},
		{Protocol: "tcp", FromPort: 53, ToPort: 53, SourceSG: resolver},
	}
}

func AsAny(rules []Rule) []any {
	out := make([]any, 0, len(rules))
	for _, rule := range rules {
		if IsOpenWorldSSH(rule) {
			continue
		}
		out = append(out, rule.AsValue())
	}
	return out
}

func GroupID(config types.Value) string {
	return types.Identifier("sg", config["app"], config["environment"])
}
