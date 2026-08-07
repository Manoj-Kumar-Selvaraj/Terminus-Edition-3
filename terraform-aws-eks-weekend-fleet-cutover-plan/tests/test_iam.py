"""Cluster, node and workload identity roles, and their permission envelopes."""

from __future__ import annotations

import json

import pytest
from conftest import afters, as_set, keyed, only, statements

CLUSTER_MANAGED_POLICIES = {
    "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
}

NODE_MANAGED_POLICIES = {
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
}

NODE_LOG_ACTIONS = {
    "logs:CreateLogStream",
    "logs:DescribeLogStreams",
    "logs:PutLogEvents",
}

IRSA_ENVELOPES = {
    "ebs-csi": {
        "discovery": {
            "ec2:DescribeAvailabilityZones",
            "ec2:DescribeInstances",
            "ec2:DescribeSnapshots",
            "ec2:DescribeTags",
            "ec2:DescribeVolumes",
            "ec2:DescribeVolumesModifications",
        },
        "mutation": {
            "ec2:AttachVolume",
            "ec2:CreateSnapshot",
            "ec2:CreateTags",
            "ec2:DeleteSnapshot",
            "ec2:DeleteVolume",
            "ec2:DetachVolume",
            "ec2:ModifyVolume",
        },
        "condition_key": "aws:ResourceTag/kubernetes.io/cluster/{cluster}",
        "condition_value": "owned",
    },
    "cluster-autoscaler": {
        "discovery": {
            "autoscaling:DescribeAutoScalingGroups",
            "autoscaling:DescribeAutoScalingInstances",
            "autoscaling:DescribeLaunchConfigurations",
            "autoscaling:DescribeScalingActivities",
            "autoscaling:DescribeTags",
            "ec2:DescribeInstanceTypes",
            "ec2:DescribeLaunchTemplateVersions",
            "eks:DescribeNodegroup",
        },
        "mutation": {
            "autoscaling:SetDesiredCapacity",
            "autoscaling:TerminateInstanceInAutoScalingGroup",
            "autoscaling:UpdateAutoScalingGroup",
        },
        "condition_key": "autoscaling:ResourceTag/kubernetes.io/cluster/{cluster}",
        "condition_value": "owned",
    },
    "aws-load-balancer-controller": {
        "discovery": {
            "ec2:DescribeAvailabilityZones",
            "ec2:DescribeSecurityGroups",
            "ec2:DescribeSubnets",
            "ec2:DescribeVpcs",
            "elasticloadbalancing:DescribeListeners",
            "elasticloadbalancing:DescribeLoadBalancers",
            "elasticloadbalancing:DescribeTargetGroups",
            "elasticloadbalancing:DescribeTargetHealth",
        },
        "mutation": {
            "elasticloadbalancing:AddTags",
            "elasticloadbalancing:DeleteLoadBalancer",
            "elasticloadbalancing:DeleteTargetGroup",
            "elasticloadbalancing:DeregisterTargets",
            "elasticloadbalancing:ModifyListener",
            "elasticloadbalancing:ModifyTargetGroup",
            "elasticloadbalancing:RegisterTargets",
        },
        "condition_key": "elasticloadbalancing:ResourceTag/elbv2.k8s.aws/cluster",
        "condition_value": "{cluster}",
    },
}


def roles_by_name(plan):
    """Every planned IAM role indexed by role name."""
    return keyed(afters(plan, "aws_iam_role"), "name")


def attachments(plan, role_name):
    """Managed policy ARNs attached to one role."""
    return {
        planned["policy_arn"]
        for planned in afters(plan, "aws_iam_role_policy_attachment")
        if planned["role"] == role_name
    }


def inline_policies(plan, role_name):
    """Inline policies on one role, indexed by policy name."""
    return keyed(
        [p for p in afters(plan, "aws_iam_role_policy") if p["role"] == role_name],
        "name",
    )


def test_cluster_role_is_assumable_only_by_the_eks_service(plan, inventory):
    """The control plane role trusts eks.amazonaws.com through sts:AssumeRole."""
    name = f"{inventory['resource_prefix']}-eks-cluster"
    role = roles_by_name(plan)[name]

    trust = statements(role["assume_role_policy"])
    entry = only(list(trust.values()), "cluster trust statement")
    assert entry["Effect"] == "Allow"
    assert entry["Principal"] == {"Service": "eks.amazonaws.com"}
    assert as_set(entry["Action"]) == {"sts:AssumeRole"}

    assert attachments(plan, name) == CLUSTER_MANAGED_POLICIES


def test_node_role_is_assumable_by_ec2_and_carries_the_worker_policies(plan, inventory):
    """The node role trusts ec2.amazonaws.com and holds the four managed policies."""
    name = f"{inventory['resource_prefix']}-eks-node"
    role = roles_by_name(plan)[name]

    trust = statements(role["assume_role_policy"])
    entry = only(list(trust.values()), "node trust statement")
    assert entry["Principal"] == {"Service": "ec2.amazonaws.com"}
    assert as_set(entry["Action"]) == {"sts:AssumeRole"}

    assert attachments(plan, name) == NODE_MANAGED_POLICIES


def test_nodes_join_through_an_instance_profile_wrapping_the_node_role(plan, inventory):
    """A single instance profile named by convention wraps the node role."""
    name = f"{inventory['resource_prefix']}-eks-node"
    profile = only(afters(plan, "aws_iam_instance_profile"), "node instance profile")

    assert profile["name"] == name
    assert profile["role"] == name


def test_node_log_delivery_is_scoped_to_the_cluster_log_group(plan, inventory):
    """The node inline policy grants three log actions on the cluster log group only."""
    role_name = f"{inventory['resource_prefix']}-eks-node"
    policies = inline_policies(plan, role_name)
    assert set(policies) == {f"{role_name}-cluster-logs"}, sorted(policies)

    entry = statements(policies[f"{role_name}-cluster-logs"]["policy"])
    assert set(entry) == {"ScopedClusterLogDelivery"}, sorted(entry)

    scoped = entry["ScopedClusterLogDelivery"]
    assert scoped["Effect"] == "Allow"
    assert as_set(scoped["Action"]) == NODE_LOG_ACTIONS

    expected_resource = (
        f"arn:aws:logs:{inventory['region']}:{inventory['account_id']}"
        f":log-group:/aws/eks/{inventory['cluster_name']}/cluster:*"
    )
    assert as_set(scoped["Resource"]) == {expected_resource}


@pytest.mark.parametrize("identity", sorted(IRSA_ENVELOPES))
def test_irsa_role_trusts_only_its_own_service_account(plan, inventory, identity):
    """Each IRSA role is pinned to one OIDC audience and one service account subject."""
    spec = inventory["irsa_roles"][identity]
    role_name = f"{inventory['resource_prefix']}-irsa-{identity}"
    role = roles_by_name(plan)[role_name]

    trust = statements(role["assume_role_policy"])
    entry = only(list(trust.values()), f"{identity} trust statement")
    assert entry["Effect"] == "Allow"
    assert as_set(entry["Action"]) == {"sts:AssumeRoleWithWebIdentity"}
    assert entry["Principal"] == {"Federated": inventory["oidc_provider_arn"]}

    url = inventory["oidc_provider_url"]
    condition = entry["Condition"]["StringEquals"]
    subject = f"system:serviceaccount:{spec['namespace']}:{spec['service_account']}"
    assert condition == {f"{url}:aud": "sts.amazonaws.com", f"{url}:sub": subject}


@pytest.mark.parametrize("identity", sorted(IRSA_ENVELOPES))
def test_irsa_policy_splits_open_discovery_from_cluster_scoped_mutation(
    plan, inventory, identity
):
    """Read actions are unconditional, mutating actions are pinned to this cluster."""
    envelope = IRSA_ENVELOPES[identity]
    cluster = inventory["cluster_name"]
    role_name = f"{inventory['resource_prefix']}-irsa-{identity}"

    policies = inline_policies(plan, role_name)
    assert set(policies) == {f"{role_name}-inline"}, sorted(policies)

    entries = statements(policies[f"{role_name}-inline"]["policy"])
    assert set(entries) == {"Discovery", "ScopedMutation"}, sorted(entries)

    discovery = entries["Discovery"]
    assert discovery["Effect"] == "Allow"
    assert as_set(discovery["Action"]) == envelope["discovery"]
    assert "Condition" not in discovery

    mutation = entries["ScopedMutation"]
    assert mutation["Effect"] == "Allow"
    assert as_set(mutation["Action"]) == envelope["mutation"]
    assert mutation["Condition"] == {
        "StringEquals": {
            envelope["condition_key"].format(cluster=cluster): envelope[
                "condition_value"
            ].format(cluster=cluster)
        }
    }


def test_no_planned_iam_policy_grants_blanket_privilege(plan):
    """No inline or trust policy anywhere in the plan allows a wildcard action."""
    documents = [role["assume_role_policy"] for role in afters(plan, "aws_iam_role")]
    documents += [policy["policy"] for policy in afters(plan, "aws_iam_role_policy")]

    for raw in documents:
        for entry in json.loads(raw)["Statement"]:
            if entry.get("Effect") != "Allow":
                continue
            for action in as_set(entry["Action"]):
                assert not action.endswith("*"), f"wildcard action granted: {action}"
