package identity

import (
	"fleetrollout/internal/types"
)

func Release(config types.Value) types.Value {
	artifact := types.Object(config["release_artifact"])
	result := types.Value{}
	for _, key := range types.ManifestFields {
		result[key] = artifact[key]
	}
	result["manifest_sha256"] = types.ManifestDigest(artifact)
	return result
}

func MetadataOptions() types.Value {
	return types.Value{
		"http_tokens":                 "required",
		"http_endpoint":               "enabled",
		"http_put_response_hop_limit": 1,
	}
}

func LaunchTemplate(config types.Value) types.Value {
	release := Release(config)
	body := types.Value{
		"ami_id":           release["ami_id"],
		"architecture":     release["architecture"],
		"instance_type":    config["instance_type"],
		"user_data_sha256": release["user_data_sha256"],
		"metadata_options": MetadataOptions(),
		"provenance": types.Value{
			"commit_sha":      release["commit_sha"],
			"build_id":        release["build_id"],
			"manifest_sha256": release["manifest_sha256"],
		},
	}
	version := types.Hash(body, 20)
	return types.Value{
		"id":               types.Identifier("lt", config["app"], config["environment"]),
		"version":          version,
		"ami_id":           body["ami_id"],
		"architecture":     body["architecture"],
		"instance_type":    body["instance_type"],
		"user_data_sha256": body["user_data_sha256"],
		"metadata_options": body["metadata_options"],
		"provenance":       body["provenance"],
		"tags": types.Value{
			"Application":           config["app"],
			"Environment":           config["environment"],
			"ManagedBy":             "terraform-aws-ec2-module",
			"CommitSha":             release["commit_sha"],
			"BuildId":               release["build_id"],
			"ReleaseManifestSha256": release["manifest_sha256"],
		},
	}
}
