"""Cross-resource consistency the review board treats as a single fixed point."""

from __future__ import annotations

import json

from conftest import afters, block, keyed
from test_addons_helm import irsa_role_arn


def planned_output(plan, name):
    """Root output value known at plan time."""
    entry = plan["planned_values"]["outputs"][name]
    assert "value" in entry, f"output {name} is unknown at plan time"
    assert entry.get("sensitive") is False, f"output {name} must not be sensitive"
    return entry["value"]

def test_addon_irsa_arns_match_planned_irsa_role_resources(plan, inventory):
    """Add-on service account roles are the same ARNs as the planned IRSA roles."""
    roles = keyed(afters(plan, "aws_iam_role"), "name")
    addons = keyed(afters(plan, "aws_eks_addon"), "addon_name")

    for addon_name, spec in inventory["cluster_addons"].items():
        identity = spec["irsa_role"]
        planned_addon = addons[addon_name]
        if not identity:
            assert not planned_addon["service_account_role_arn"], addon_name
            continue

        role_name = f"{inventory['resource_prefix']}-irsa-{identity}"
        assert role_name in roles, identity
        expected = irsa_role_arn(inventory, identity)
        assert roles[role_name]["name"] == role_name
        assert planned_addon["service_account_role_arn"] == expected, addon_name
        assert planned_output(plan, "irsa_role_arns")[identity] == expected, identity


def test_helm_role_annotations_match_the_same_irsa_arns(plan, inventory):
    """Helm IRSA annotations agree with both the IRSA roles and any matching add-on."""
    releases = keyed(afters(plan, "helm_release"), "name")
    addons = keyed(afters(plan, "aws_eks_addon"), "addon_name")
    annotation = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"

    for release_name, spec in inventory["helm_releases"].items():
        rendered = {entry["name"]: entry["value"] for entry in releases[release_name]["set"]}
        identity = spec["irsa_role"]
        if not identity:
            assert annotation not in rendered, release_name
            continue

        expected = irsa_role_arn(inventory, identity)
        assert rendered[annotation] == expected, release_name
        assert planned_output(plan, "irsa_role_arns")[identity] == expected, identity

        for addon_name, addon_spec in inventory["cluster_addons"].items():
            if addon_spec["irsa_role"] == identity:
                assert addons[addon_name]["service_account_role_arn"] == expected


def test_schedule_payloads_exclude_non_parked_node_groups(plan, inventory):
    """Core (non-parked) groups never appear in either cutover payload."""
    non_parked = {
        name for name, spec in inventory["node_groups"].items() if not spec["weekend_parked"]
    }
    assert non_parked, "inventory needs at least one non-parked node group"

    for entry in afters(plan, "aws_scheduler_schedule"):
        payload = json.loads(block(entry, "target")["input"])
        overlap = non_parked.intersection(payload["node_groups"])
        assert not overlap, f"{entry['name']} leaked non-parked groups: {sorted(overlap)}"


def test_alarm_and_schedule_outputs_match_planned_resources(plan, inventory):
    """Root outputs are sorted projections of the planned alarms and schedules."""
    prefix = inventory["resource_prefix"]
    expected_alarms = sorted(
        {f"{prefix}-{name}-node-cpu" for name in inventory["node_groups"]}
        | {f"{prefix}-cluster-node-cpu"}
    )
    expected_schedules = sorted(
        [f"{prefix}-weekend-scale-down", f"{prefix}-weekend-scale-up"]
    )

    assert planned_output(plan, "monitoring_alarm_names") == expected_alarms
    assert planned_output(plan, "weekend_schedule_names") == expected_schedules
    assert set(keyed(afters(plan, "aws_cloudwatch_metric_alarm"), "alarm_name")) == set(
        expected_alarms
    )
    assert set(keyed(afters(plan, "aws_scheduler_schedule"), "name")) == set(
        expected_schedules
    )


def test_node_instance_profile_name_matches_node_role_convention(plan, inventory):
    """The instance profile and node role share the contracted name."""
    name = f"{inventory['resource_prefix']}-eks-node"
    profiles = afters(plan, "aws_iam_instance_profile")
    assert len(profiles) == 1
    assert profiles[0]["name"] == name
    assert profiles[0]["role"] == name


def test_taggable_aws_resources_carry_cluster_tag(plan, inventory):
    """Every taggable AWS resource planned by the module carries wfleet.io/cluster."""
    expected = inventory["cluster_name"]
    taggable_types = {
        "aws_eks_cluster",
        "aws_eks_node_group",
        "aws_eks_addon",
        "aws_iam_role",
        "aws_iam_instance_profile",
        "aws_cloudwatch_log_group",
        "aws_cloudwatch_metric_alarm",
        "aws_scheduler_schedule_group",
    }
    for change in plan["resource_changes"]:
        if change["type"] not in taggable_types:
            continue
        after = change["change"]["after"]
        tags = after.get("tags") or after.get("tags_all") or {}
        assert tags.get("wfleet.io/cluster") == expected, change["address"]
