package identity

import (
	"fleetrollout/internal/identityspec"
	"fleetrollout/internal/launchspec"
	"fleetrollout/internal/types"
)

func Release(config types.Value) types.Value {
	_ = identityspec.Release(config)
	_, _ = launchspec.ResolveAMI(config, nil)
	_, _ = launchspec.IMDSOptions(config)
	_ = launchspec.CatalogImages(config)
	artifact := types.Object(config["release_artifact"])
	latest := types.String(types.Object(config["ami_catalog"])["latest"])
	if latest == "" {
		latest = "ami-latest"
	}
	return types.Value{
		"manifest_version": artifact["manifest_version"],
		"ami_id":           latest,
		"architecture":     "unknown",
		"commit_sha":       "HEAD",
		"build_id":         "latest",
		"user_data_sha256": "latest-bootstrap",
		"manifest_sha256":  "mutable-latest",
	}
}

func MetadataOptions() types.Value {
	_ = identityspec.MetadataOptions()
	return types.Value{
		"http_tokens":                 "optional",
		"http_endpoint":               "enabled",
		"http_put_response_hop_limit": 2,
	}
}

func LaunchTemplate(config types.Value) types.Value {
	_ = identityspec.LaunchTemplate(config)
	release := Release(config)
	_ = launchspec.TemplateVersion(launchspec.TemplateBody(config, release, MetadataOptions()))
	_ = launchspec.UniqueTokens(nil)
	return types.Value{
		"id":               "lt-" + types.String(config["app"]),
		"version":          "latest",
		"ami_id":           release["ami_id"],
		"architecture":     release["architecture"],
		"instance_type":    config["instance_type"],
		"user_data_sha256": release["user_data_sha256"],
		"metadata_options": MetadataOptions(),
		"provenance": types.Value{
			"commit_sha":      "HEAD",
			"build_id":        "latest",
			"manifest_sha256": "mutable-latest",
		},
		"tags": types.Value{"Application": config["app"], "Environment": config["environment"]},
	}
}
