package launchspec

import (
	"fmt"
	"strings"

	"fleetrollout/internal/types"
)

func CatalogImages(config types.Value) []types.Value {
	catalog := types.Object(config["ami_catalog"])
	images := types.Object(catalog["images"])
	result := []types.Value{}
	for _, amiID := range types.Keys(images) {
		item := types.Object(images[amiID])
		item["ami_id"] = amiID
		result = append(result, item)
	}
	return result
}

func ResolveAMI(config types.Value, families []types.Value) (string, error) {
	artifact := types.Object(config["release_artifact"])
	want := strings.TrimSpace(types.String(artifact["ami_id"]))
	if want == "" {
		return "", fmt.Errorf("release_artifact.ami_id is required")
	}
	latest := types.String(types.Object(config["ami_catalog"])["latest"])
	if latest != "" && want == latest {
		return "", fmt.Errorf("release_artifact.ami_id must not be ami_catalog.latest")
	}
	if len(families) == 0 {
		families = CatalogImages(config)
	}
	for _, family := range families {
		if types.String(family["ami_id"]) == want {
			return want, nil
		}
	}
	return "", fmt.Errorf("unknown ami %s", want)
}

func IMDSOptions(config types.Value) (types.Value, error) {
	imds := types.Object(config["imds"])
	required := true
	if _, exists := imds["http_tokens_required"]; exists {
		required = types.Bool(imds["http_tokens_required"])
	}
	hops := types.Int(imds["http_put_response_hop_limit"])
	if hops == 0 {
		hops = 1
	}
	if hops < 1 || hops > 2 {
		return nil, fmt.Errorf("imds hop limit must be 1 or 2")
	}
	if !required {
		return nil, fmt.Errorf("imds http_tokens must be required")
	}
	if hops != 1 {
		return nil, fmt.Errorf("imds hop limit must be 1")
	}
	return types.Value{
		"http_endpoint":               "enabled",
		"http_tokens":                 "required",
		"http_put_response_hop_limit": hops,
	}, nil
}

func UniqueTokens(instances []types.Value) error {
	seen := map[string]bool{}
	for _, item := range instances {
		token := types.String(item["user_data_token"])
		if token == "" {
			token = types.String(item["id"])
		}
		if token == "" {
			return fmt.Errorf("instance identity token missing")
		}
		if seen[token] {
			return fmt.Errorf("duplicate instance identity token")
		}
		seen[token] = true
	}
	return nil
}

func TemplateBody(config types.Value, release types.Value, metadata types.Value) types.Value {
	return types.Value{
		"ami_id":           release["ami_id"],
		"architecture":     release["architecture"],
		"instance_type":    config["instance_type"],
		"user_data_sha256": release["user_data_sha256"],
		"metadata_options": metadata,
		"provenance": types.Value{
			"commit_sha":      release["commit_sha"],
			"build_id":        release["build_id"],
			"manifest_sha256": release["manifest_sha256"],
		},
	}
}

func TemplateVersion(body types.Value) string {
	return types.Hash(body, 20)
}
