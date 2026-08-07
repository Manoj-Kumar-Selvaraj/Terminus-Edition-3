"""CloudWatch alarm coverage and the Friday/Monday EventBridge cutover."""

from __future__ import annotations

import json

from conftest import afters, block, keyed, only


def alarms(plan):
    """Every planned CloudWatch alarm indexed by alarm name."""
    return keyed(afters(plan, "aws_cloudwatch_metric_alarm"), "alarm_name")


def assert_common_alarm_shape(planned, inventory, label):
    """Shared statistic, comparison, window and notification wiring."""
    monitoring = inventory["monitoring"]
    topic = monitoring["alarm_topic_arn"]

    assert planned["namespace"] == monitoring["metric_namespace"], label
    assert planned["metric_name"] == monitoring["node_cpu_metric"], label
    assert planned["statistic"] == "Average", label
    assert planned["comparison_operator"] == "GreaterThanOrEqualToThreshold", label
    assert planned["period"] == monitoring["period_seconds"], label
    assert planned["evaluation_periods"] == monitoring["evaluation_periods"], label
    assert planned["treat_missing_data"] == "breaching", label
    assert planned["alarm_actions"] == [topic], label
    assert planned["ok_actions"] == [topic], label


def test_alarm_coverage_is_one_per_node_group_plus_one_fleet_wide(plan, inventory):
    """The alarm set is exactly the per-node-group alarms and the cluster alarm."""
    prefix = inventory["resource_prefix"]
    expected = {f"{prefix}-{name}-node-cpu" for name in inventory["node_groups"]}
    expected.add(f"{prefix}-cluster-node-cpu")

    assert set(alarms(plan)) == expected


def test_node_group_alarms_use_their_own_threshold_and_dimensions(plan, inventory):
    """Each node group alarm watches its own group at its own inventory threshold."""
    prefix = inventory["resource_prefix"]
    planned_alarms = alarms(plan)

    for name, spec in inventory["node_groups"].items():
        planned = planned_alarms[f"{prefix}-{name}-node-cpu"]
        assert_common_alarm_shape(planned, inventory, name)
        assert planned["threshold"] == spec["cpu_alarm_threshold_pct"], name
        assert planned["dimensions"] == {
            "ClusterName": inventory["cluster_name"],
            "NodegroupName": name,
        }, name


def test_fleet_wide_alarm_watches_the_cluster_dimension_only(plan, inventory):
    """The cluster alarm uses the cluster threshold and no node group dimension."""
    prefix = inventory["resource_prefix"]
    planned = alarms(plan)[f"{prefix}-cluster-node-cpu"]

    assert_common_alarm_shape(planned, inventory, "cluster")
    assert planned["threshold"] == inventory["monitoring"]["cluster_cpu_threshold_pct"]
    assert planned["dimensions"] == {"ClusterName": inventory["cluster_name"]}


def test_cutover_schedules_live_in_the_inventory_schedule_group(plan, inventory):
    """A single schedule group named by the inventory owns both schedules."""
    schedule = inventory["weekend_schedule"]
    group = only(afters(plan, "aws_scheduler_schedule_group"), "schedule group")
    assert group["name"] == schedule["group_name"]

    planned = afters(plan, "aws_scheduler_schedule")
    assert len(planned) == 2, f"expected two schedules, found {len(planned)}"
    assert {entry["group_name"] for entry in planned} == {schedule["group_name"]}


def test_both_schedules_fire_on_their_contracted_cron_in_the_local_timezone(plan, inventory):
    """Friday scales down, Monday scales up, both enabled with a flexible window."""
    schedule = inventory["weekend_schedule"]
    prefix = inventory["resource_prefix"]
    planned = keyed(afters(plan, "aws_scheduler_schedule"), "name")

    expected_crons = {
        f"{prefix}-weekend-scale-down": schedule["scale_down_cron"],
        f"{prefix}-weekend-scale-up": schedule["scale_up_cron"],
    }
    assert set(planned) == set(expected_crons), sorted(planned)

    for name, cron in expected_crons.items():
        entry = planned[name]
        assert entry["schedule_expression"] == cron, name
        assert entry["schedule_expression_timezone"] == schedule["timezone"], name
        assert entry["state"] == "ENABLED", name

        window = block(entry, "flexible_time_window")
        assert window["mode"] == "FLEXIBLE", name
        assert window["maximum_window_in_minutes"] == schedule["flexible_window_minutes"], name


def test_schedules_invoke_the_placeholder_lambda_under_the_scheduler_role(plan, inventory):
    """Both schedules target the inventory Lambda ARN with the inventory role."""
    schedule = inventory["weekend_schedule"]

    for entry in afters(plan, "aws_scheduler_schedule"):
        target = block(entry, "target")
        assert target["arn"] == schedule["target_lambda_arn"], entry["name"]
        assert target["role_arn"] == schedule["scheduler_role_arn"], entry["name"]


def test_cutover_payloads_park_and_restore_only_the_weekend_node_groups(plan, inventory):
    """Scale-down zeroes the parked groups; scale-up restores their inventory sizes."""
    prefix = inventory["resource_prefix"]
    parked = {
        name: spec
        for name, spec in inventory["node_groups"].items()
        if spec["weekend_parked"]
    }
    assert parked, "the inventory declares no weekend-parked node group"

    expected = {
        f"{prefix}-weekend-scale-down": {
            "action": "scale-down",
            "cluster_name": inventory["cluster_name"],
            "region": inventory["region"],
            "node_groups": {
                name: {"min_size": 0, "desired_size": 0} for name in parked
            },
        },
        f"{prefix}-weekend-scale-up": {
            "action": "scale-up",
            "cluster_name": inventory["cluster_name"],
            "region": inventory["region"],
            "node_groups": {
                name: {
                    "min_size": spec["min_size"],
                    "desired_size": spec["desired_size"],
                }
                for name, spec in parked.items()
            },
        },
    }

    planned = keyed(afters(plan, "aws_scheduler_schedule"), "name")
    for name, payload in expected.items():
        assert json.loads(block(planned[name], "target")["input"]) == payload, name
