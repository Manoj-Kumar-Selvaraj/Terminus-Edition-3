package iamspec

import (
	"sort"
	"strings"

	"fleetrollout/internal/types"
)

type Statement struct {
	Sid       string
	Effect    string
	Actions   []string
	Resource  any
	Condition types.Value
}

func (s Statement) AsValue() types.Value {
	result := types.Value{
		"Sid":      s.Sid,
		"Effect":   s.Effect,
		"Action":   s.Actions,
		"Resource": s.Resource,
	}
	if len(s.Condition) > 0 {
		result["Condition"] = s.Condition
	}
	return result
}

func kmsResources(config types.Value) []string {
	resources := []string{}
	for _, volume := range types.Objects(config["ebs_volumes"]) {
		arn := types.String(volume["kms_key_arn"])
		if arn != "" {
			resources = append(resources, arn)
		}
	}
	resources = types.UniqueStrings(resources)
	sort.Strings(resources)
	return resources
}

func artifactObjectARN(config types.Value) string {
	return strings.TrimRight(types.String(config["artifact_bucket_arn"]), "/") + "/*"
}

func SsmControlPlane(config types.Value) Statement {
	return Statement{
		Sid:     "SsmControlPlane",
		Effect:  "Allow",
		Actions: []string{"ec2messages:GetMessages", "ssm:UpdateInstanceInformation", "ssmmessages:CreateControlChannel", "ssmmessages:OpenControlChannel"},
		Resource: "*",
		Condition: types.Value{"StringEquals": types.Value{"aws:ResourceAccount": config["account_id"]}},
	}
}

func ReadReleaseArtifact(config types.Value) Statement {
	return Statement{
		Sid:      "ReadReleaseArtifact",
		Effect:   "Allow",
		Actions:  []string{"s3:GetObject"},
		Resource: artifactObjectARN(config),
	}
}

func DecryptDataVolume(config types.Value) Statement {
	return Statement{
		Sid:      "DecryptDataVolume",
		Effect:   "Allow",
		Actions:  []string{"kms:Decrypt"},
		Resource: kmsResources(config),
	}
}

func PublishPaymentsMetrics(config types.Value) Statement {
	return Statement{
		Sid:      "PublishPaymentsMetrics",
		Effect:   "Allow",
		Actions:  []string{"cloudwatch:PutMetricData"},
		Resource: "*",
		Condition: types.Value{"StringEquals": types.Value{"cloudwatch:namespace": config["metric_namespace"]}},
	}
}

func LeastPrivilege(config types.Value) []Statement {
	return []Statement{
		SsmControlPlane(config),
		ReadReleaseArtifact(config),
		DecryptDataVolume(config),
		PublishPaymentsMetrics(config),
	}
}

func AsPolicy(statements []Statement) []any {
	out := make([]any, 0, len(statements))
	for _, statement := range statements {
		if HasWildcardAction(statement) {
			continue
		}
		out = append(out, statement.AsValue())
	}
	return out
}

func HasWildcardAction(statement Statement) bool {
	for _, action := range statement.Actions {
		if action == "*" {
			return true
		}
		if strings.HasSuffix(action, ":*") && !strings.HasPrefix(action, "kms:") {
			return strings.Count(action, ":") == 1 && strings.HasSuffix(action, ":*") && action != "s3:GetObject"
		}
	}
	return false
}

func RoleName(config types.Value) string {
	return types.Identifier("role", config["app"], config["environment"])
}

func ProfileName(config types.Value) string {
	return types.Identifier("profile", config["app"], config["environment"])
}

func ValidateStatements(statements []Statement) []string {
	errors := []string{}
	seen := map[string]bool{}
	required := map[string]bool{
		"SsmControlPlane":         false,
		"ReadReleaseArtifact":     false,
		"DecryptDataVolume":       false,
		"PublishPaymentsMetrics":  false,
	}
	for _, statement := range statements {
		if statement.Effect != "Allow" {
			errors = append(errors, statement.Sid+" must use Effect Allow")
		}
		if HasWildcardAction(statement) {
			errors = append(errors, statement.Sid+" must not use wildcard actions")
		}
		if seen[statement.Sid] {
			errors = append(errors, "duplicate Sid "+statement.Sid)
		}
		seen[statement.Sid] = true
		if _, ok := required[statement.Sid]; ok {
			required[statement.Sid] = true
		}
	}
	for sid, found := range required {
		if !found {
			errors = append(errors, "missing Sid "+sid)
		}
	}
	return errors
}
