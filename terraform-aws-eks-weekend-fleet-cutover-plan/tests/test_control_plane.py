"""Control plane endpoint posture, logging and the managed node group fleet."""

from __future__ import annotations

from conftest import afters, block, keyed, only


def baseline_tags(inventory):
    """Inventory tags plus the mandatory cluster tag."""
    return dict(inventory["tags"], **{"wfleet.io/cluster": inventory["cluster_name"]})


def test_cluster_api_endpoint_is_private_only(plan, inventory):
    """The API server is reachable inside the VPC and nowhere else."""
    cluster = only(afters(plan, "aws_eks_cluster"), "EKS cluster")
    vpc_config = block(cluster, "vpc_config")

    assert vpc_config["endpoint_private_access"] is True
    assert vpc_config["endpoint_public_access"] is False
    assert vpc_config["subnet_ids"] == inventory["private_subnet_ids"]
    assert vpc_config["security_group_ids"] == [inventory["cluster_security_group_id"]]


def test_cluster_runs_the_contracted_version_and_log_types(plan, inventory):
    """Cluster version, name and the enabled log types match the inventory exactly."""
    cluster = only(afters(plan, "aws_eks_cluster"), "EKS cluster")

    assert cluster["name"] == inventory["cluster_name"]
    assert cluster["version"] == inventory["kubernetes_version"]
    assert set(cluster["enabled_cluster_log_types"]) == set(inventory["cluster_log_types"])
    assert cluster["tags"] == baseline_tags(inventory)


def test_control_plane_log_group_uses_the_contracted_name_and_retention(plan, inventory):
    """The control plane log group exists at the conventional path and retention."""
    group = only(afters(plan, "aws_cloudwatch_log_group"), "control plane log group")

    assert group["name"] == f"/aws/eks/{inventory['cluster_name']}/cluster"
    assert group["retention_in_days"] == inventory["cluster_log_retention_days"]
    assert group["tags"] == baseline_tags(inventory)


def test_every_inventory_node_group_is_planned_once(plan, inventory):
    """The fleet holds exactly the node groups the inventory declares."""
    groups = keyed(afters(plan, "aws_eks_node_group"), "node_group_name")
    assert set(groups) == set(inventory["node_groups"])


def test_node_groups_carry_their_own_ami_capacity_and_scaling_profile(plan, inventory):
    """Each node group's AMI, capacity, disk and scaling settings come from the inventory."""
    groups = keyed(afters(plan, "aws_eks_node_group"), "node_group_name")

    for name, spec in inventory["node_groups"].items():
        planned = groups[name]
        assert planned["cluster_name"] == inventory["cluster_name"], name
        assert planned["capacity_type"] == spec["capacity_type"], name
        assert planned["ami_type"] == spec["ami_type"], name
        assert planned["release_version"] == spec["release_version"], name
        assert planned["instance_types"] == spec["instance_types"], name
        assert planned["disk_size"] == spec["disk_size_gb"], name
        assert planned["labels"] == spec["labels"], name
        assert planned["subnet_ids"] == inventory["private_subnet_ids"], name

        scaling = block(planned, "scaling_config")
        assert scaling["min_size"] == spec["min_size"], name
        assert scaling["desired_size"] == spec["desired_size"], name
        assert scaling["max_size"] == spec["max_size"], name

        update = block(planned, "update_config")
        assert update["max_unavailable"] == spec["max_unavailable"], name


def test_node_groups_are_discoverable_by_the_cluster_autoscaler(plan, inventory):
    """Node group tags carry the baseline tags plus the autoscaler discovery pair."""
    cluster_name = inventory["cluster_name"]
    expected = dict(
        baseline_tags(inventory),
        **{
            "k8s.io/cluster-autoscaler/enabled": "true",
            f"k8s.io/cluster-autoscaler/{cluster_name}": "owned",
        },
    )

    groups = keyed(afters(plan, "aws_eks_node_group"), "node_group_name")
    for name, planned in groups.items():
        assert planned["tags"] == expected, name


def test_node_groups_use_the_shared_node_role_arn(plan, inventory):
    """Every node group joins through the conventional node role ARN."""
    expected = "arn:aws:iam::{account}:role/{prefix}-eks-node".format(
        account=inventory["account_id"], prefix=inventory["resource_prefix"]
    )
    for planned in afters(plan, "aws_eks_node_group"):
        assert planned["node_role_arn"] == expected, planned["node_group_name"]
