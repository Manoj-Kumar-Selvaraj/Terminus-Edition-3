"""The ALB ingress surface and the five outputs the review board reads."""

from __future__ import annotations

from conftest import afters, block, only


def test_ingress_class_is_backed_by_the_alb_controller(plan, inventory):
    """One ingress class, named by the inventory, wired to the inventory controller."""
    spec = inventory["ingress"]
    planned = only(afters(plan, "kubernetes_ingress_class_v1"), "ingress class")

    assert block(planned, "metadata")["name"] == spec["ingress_class_name"]
    assert block(planned, "spec")["controller"] == spec["controller"]


def test_placeholder_ingress_is_annotated_and_bound_to_that_class(plan, inventory):
    """The placeholder lives in the inventory namespace with the ALB annotations."""
    spec = inventory["ingress"]
    planned = only(afters(plan, "kubernetes_ingress_v1"), "placeholder ingress")

    metadata = block(planned, "metadata")
    assert metadata["name"] == spec["placeholder_name"]
    assert metadata["namespace"] == spec["namespace"]
    assert metadata["annotations"] == {
        "alb.ingress.kubernetes.io/scheme": spec["scheme"],
        "alb.ingress.kubernetes.io/target-type": spec["target_type"],
    }
    assert block(planned, "spec")["ingress_class_name"] == spec["ingress_class_name"]


def test_placeholder_ingress_routes_the_contracted_host_and_path(plan, inventory):
    """Host, prefix path and backend service all come from the inventory."""
    spec = inventory["ingress"]
    planned = only(afters(plan, "kubernetes_ingress_v1"), "placeholder ingress")

    rule = only(block(planned, "spec")["rule"], "ingress rule")
    assert rule["host"] == spec["placeholder_host"]

    path = only(block(rule, "http")["path"], "ingress path")
    assert path["path"] == "/"
    assert path["path_type"] == "Prefix"

    service = block(block(path, "backend"), "service")
    assert service["name"] == spec["service_name"]
    assert block(service, "port")["number"] == spec["service_port"]


def test_root_outputs_are_the_five_contracted_keys(plan):
    """The board reads exactly five outputs, all resolved at plan time."""
    outputs = plan["planned_values"]["outputs"]
    assert set(outputs) == {
        "cluster_name",
        "node_group_names",
        "irsa_role_arns",
        "weekend_schedule_names",
        "monitoring_alarm_names",
    }
    for name, body in outputs.items():
        assert "value" in body, f"{name} is not known at plan time"
        assert body.get("sensitive") is False, name


def test_output_values_summarise_the_planned_fleet(plan, inventory):
    """Each output reports the sorted, fully composed view the contract specifies."""
    prefix = inventory["resource_prefix"]
    account = inventory["account_id"]
    outputs = {name: body["value"] for name, body in plan["planned_values"]["outputs"].items()}

    assert outputs["cluster_name"] == inventory["cluster_name"]
    assert outputs["node_group_names"] == sorted(inventory["node_groups"])
    assert outputs["irsa_role_arns"] == {
        identity: f"arn:aws:iam::{account}:role/{prefix}-irsa-{identity}"
        for identity in inventory["irsa_roles"]
    }
    assert outputs["weekend_schedule_names"] == [
        f"{prefix}-weekend-scale-down",
        f"{prefix}-weekend-scale-up",
    ]
    assert outputs["monitoring_alarm_names"] == sorted(
        [f"{prefix}-{name}-node-cpu" for name in inventory["node_groups"]]
        + [f"{prefix}-cluster-node-cpu"]
    )
