package validate

import (
	"fmt"
	"strings"

	"fleetrollout/internal/ipam"
	"fleetrollout/internal/types"
)

func Config(config types.Value) error {
	errors := []string{}
	if types.String(config["schema_version"]) != types.ConfigSchema {
		errors = append(errors, "schema_version must be ec2-module-config.v2")
	}
	artifact := types.Object(config["release_artifact"])
	for _, field := range append(types.ManifestFields, "manifest_sha256") {
		types.Require(artifact[field], "release_artifact."+field, &errors)
	}
	catalog, err := ipam.Open("")
	if err != nil {
		return err
	}
	defer catalog.Close()
	if len(errors) == 0 {
		if types.String(artifact["manifest_sha256"]) != types.ManifestDigest(artifact) {
			errors = append(errors, "release_artifact.manifest_sha256 does not match canonical manifest")
		}
		amiID := types.String(artifact["ami_id"])
		if _, err := catalog.ApprovedImage(amiID, types.String(artifact["ami_owner_account_id"]), types.String(artifact["architecture"])); err != nil {
			errors = append(errors, err.Error())
		}
		latest := types.String(types.Object(config["ami_catalog"])["latest"])
		if amiID != "" && amiID == latest {
			errors = append(errors, "release_artifact.ami_id must not be ami_catalog.latest")
		}
	}

	asg := types.Object(config["asg"])
	desired, minimum, maximum := types.Int(asg["desired_capacity"]), types.Int(asg["min_size"]), types.Int(asg["max_size"])
	if desired <= 0 || desired < minimum || desired > maximum {
		errors = append(errors, "asg desired_capacity must be within min_size and max_size")
	}
	if types.Int(asg["max_unavailable"]) != 1 {
		errors = append(errors, "asg.max_unavailable must be exactly 1")
	}
	if types.Int(asg["pilot_size"]) != 1 {
		errors = append(errors, "asg.pilot_size must be exactly 1")
	}
	if types.Int(asg["wave_size"]) < 1 {
		errors = append(errors, "asg.wave_size must be positive")
	}

	placement := types.Object(config["placement"])
	account := types.String(config["account_id"])
	region := types.String(config["region"])
	seenIDs, seenAZs := map[string]bool{}, map[string]bool{}
	for _, subnet := range types.Objects(placement["subnets"]) {
		id := types.String(subnet["id"])
		record, lookupErr := catalog.EligibleAppSubnet(id, account)
		if lookupErr != nil {
			errors = append(errors, lookupErr.Error())
			continue
		}
		az := record.AZ
		if types.String(subnet["az"]) != "" && types.String(subnet["az"]) != az {
			errors = append(errors, fmt.Sprintf("subnet %s availability zone does not match ipam", id))
		}
		if !strings.HasPrefix(id, "subnet-") {
			errors = append(errors, "subnet id must start with subnet-")
		}
		if !strings.HasPrefix(az, region) {
			errors = append(errors, fmt.Sprintf("subnet %s has invalid availability zone", id))
		}
		if seenIDs[id] {
			errors = append(errors, "duplicate subnet id "+id)
		}
		if seenAZs[az] {
			errors = append(errors, "duplicate availability zone "+az)
		}
		seenIDs[id], seenAZs[az] = true, true
	}
	minimumAZs := types.Int(placement["minimum_azs"])
	if len(seenAZs) < minimumAZs {
		errors = append(errors, fmt.Sprintf("placement requires at least %d unique availability zones", minimumAZs))
	}

	network := types.Object(config["network"])
	alb, resolver := types.String(network["alb_security_group_id"]), types.String(network["resolver_security_group_id"])
	prefixLists := types.StringList(network["endpoint_prefix_lists"])
	if !strings.HasPrefix(alb, "sg-") {
		errors = append(errors, "network.alb_security_group_id must start with sg-")
	}
	if !strings.HasPrefix(resolver, "sg-") {
		errors = append(errors, "network.resolver_security_group_id must start with sg-")
	}
	if len(prefixLists) == 0 {
		errors = append(errors, "network.endpoint_prefix_lists is required")
	}
	seenPrefixes := map[string]bool{}
	for _, prefix := range prefixLists {
		if seenPrefixes[prefix] {
			errors = append(errors, "network.endpoint_prefix_lists contains duplicates")
		}
		seenPrefixes[prefix] = true
		if !strings.HasPrefix(prefix, "pl-") {
			errors = append(errors, "network.endpoint_prefix_lists entries must start with pl-")
		}
	}
	port := types.Int(config["service_port"])
	if port < 1 || port > 65535 {
		errors = append(errors, "service_port must be between 1 and 65535")
	}
	types.Require(types.Object(config["rollout"])["owner_token"], "rollout.owner_token", &errors)

	seenNames := map[string]bool{}
	for _, volume := range types.Objects(config["ebs_volumes"]) {
		name := types.String(volume["logical_name"])
		if name == "" {
			errors = append(errors, "ebs_volumes.logical_name is required")
		} else if seenNames[name] {
			errors = append(errors, "duplicate ebs logical_name "+name)
		}
		seenNames[name] = true
		if !types.Bool(volume["encrypted"]) {
			errors = append(errors, fmt.Sprintf("ebs volume %s is unencrypted", name))
		}
		if types.String(volume["kms_key_alias"]) == "" {
			errors = append(errors, fmt.Sprintf("ebs volume %s is missing kms_key_alias", name))
		}
		expectedPrefix := fmt.Sprintf("arn:aws:kms:%s:%s:key/", region, account)
		if !strings.HasPrefix(types.String(volume["kms_key_arn"]), expectedPrefix) {
			errors = append(errors, fmt.Sprintf("ebs volume %s kms key is outside configured account", name))
		}
		if types.Bool(volume["delete_on_termination"]) {
			errors = append(errors, fmt.Sprintf("ebs volume %s must set delete_on_termination false", name))
		}
	}
	return types.JoinErrors(errors)
}
