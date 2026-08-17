package render

import (
	"fleetrollout/internal/drift"
	"fleetrollout/internal/iam"
	"fleetrollout/internal/identity"
	"fleetrollout/internal/importdata"
	"fleetrollout/internal/inventory"
	"fleetrollout/internal/network"
	"fleetrollout/internal/placement"
	"fleetrollout/internal/rollout"
	"fleetrollout/internal/types"
	"fleetrollout/internal/validate"
	"fleetrollout/internal/volume"
)

func Render(config types.Value, priorState types.Value) (types.Value, error) {
	if err := validate.Config(config); err != nil {
		return nil, err
	}
	prior, importReport, err := importdata.Normalize(priorState, config)
	if err != nil {
		return nil, err
	}
	release := identity.Release(config)
	template := identity.LaunchTemplate(config)
	group := network.SecurityGroup(config)
	role := iam.Role(config)
	desired := types.Int(types.Object(config["asg"])["desired_capacity"])
	priorInstances := types.Objects(prior["instances"])
	priorRefresh := types.Object(types.Object(prior["autoscaling_group"])["instance_refresh"])
	inProgress := types.String(priorRefresh["status"]) == "in_progress"
	releaseChanged := len(prior) > 0 && types.String(types.Object(prior["release_identity"])["manifest_sha256"]) != types.String(release["manifest_sha256"])
	controlLost := false
	instances := []types.Value{}
	actions := []any{}
	driftReport := []types.Value{}
	refreshState := types.Value{}
	if len(prior) == 0 {
		instances = placement.Initial(config, template, group, desired)
		refreshState = rollout.StableRefresh(config, release, desired)
		for _, item := range instances {
			actions = append(actions, types.Value{"action": "create", "slot": item["slot"], "instance_id": item["id"]})
		}
	} else if releaseChanged || inProgress {
		instances, refreshState, controlLost, err = rollout.Refresh(config, prior, template, group, desired)
		if err != nil {
			return nil, err
		}
		for _, item := range instances {
			actions = append(actions, types.Value{"action": "rolling_replace", "slot": item["slot"], "instance_id": item["id"], "operation_id": refreshState["operation_id"]})
		}
	} else {
		expected := placement.Initial(config, template, group, desired)
		driftReport = drift.Report(priorInstances, expected, group)
		instances, actions = rollout.SameRelease(config, prior, template, group, desired)
		for _, entry := range driftReport {
			actions = append(actions, types.Value{"action": types.String(entry["action"]), "instance_id": entry["instance_id"], "field": entry["field"]})
		}
		if len(priorRefresh) > 0 {
			refreshState = types.CloneValue(priorRefresh)
		} else {
			refreshState = rollout.StableRefresh(config, release, desired)
		}
	}
	volumeList, err := volume.Attachments(config, instances, prior)
	if err != nil {
		return nil, err
	}
	result := inventory.Document(
		config,
		release,
		template,
		group,
		role,
		refreshState,
		importReport,
		instances,
		volumeList,
		driftReport,
		actions,
		controlLost,
		inventory.SubnetIDs(placement.EligibleSubnets(config)),
	)
	_ = inventory.CollectStringIDs(result)
	return result, nil
}
