"""Core add-ons and the Helm releases rendered from the vendored charts."""

from __future__ import annotations

from conftest import afters, keyed

LB_CONTROLLER = "aws-load-balancer-controller"
TRIVY = "trivy"
ROLE_ARN_ANNOTATION = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"


def irsa_role_arn(inventory, identity):
    """The conventional IRSA role ARN for one workload identity."""
    return "arn:aws:iam::{account}:role/{prefix}-irsa-{identity}".format(
        account=inventory["account_id"],
        prefix=inventory["resource_prefix"],
        identity=identity,
    )


def release_set_map(planned):
    """Flatten helm_release.set into a name→value map."""
    return {entry["name"]: entry["value"] for entry in planned["set"]}


def test_every_inventory_addon_is_planned_at_its_pinned_version(plan, inventory):
    """The add-on set matches the inventory keys, versions and conflict handling."""
    addons = keyed(afters(plan, "aws_eks_addon"), "addon_name")
    assert set(addons) == set(inventory["cluster_addons"])

    for name, spec in inventory["cluster_addons"].items():
        planned = addons[name]
        assert planned["cluster_name"] == inventory["cluster_name"], name
        assert planned["addon_version"] == spec["addon_version"], name
        assert planned["resolve_conflicts_on_create"] == "OVERWRITE", name
        assert planned["resolve_conflicts_on_update"] == spec[
            "resolve_conflicts_on_update"
        ], name


def test_only_addons_with_a_declared_identity_get_a_service_account_role(plan, inventory):
    """Add-on IRSA wiring follows the inventory, with no role attached otherwise."""
    addons = keyed(afters(plan, "aws_eks_addon"), "addon_name")

    for name, spec in inventory["cluster_addons"].items():
        planned = addons[name]
        if spec["irsa_role"]:
            assert planned["service_account_role_arn"] == irsa_role_arn(
                inventory, spec["irsa_role"]
            ), name
        else:
            assert not planned["service_account_role_arn"], name


def test_helm_releases_come_from_the_vendored_charts_offline(plan, inventory):
    """Each release is named, versioned and namespaced per the inventory, with no repo."""
    releases = keyed(afters(plan, "helm_release"), "name")
    assert set(releases) == set(inventory["helm_releases"])

    for name, spec in inventory["helm_releases"].items():
        planned = releases[name]
        assert planned["namespace"] == spec["namespace"], name
        assert planned["version"] == spec["chart_version"], name
        assert not planned["repository"], name
        assert planned["create_namespace"] is False, name
        assert planned["chart"].endswith(f"charts/{spec['chart_dir']}"), planned["chart"]


def test_helm_values_carry_the_inventory_settings_and_irsa_annotation(plan, inventory):
    """Rendered set values equal the inventory values plus the service account wiring."""
    releases = keyed(afters(plan, "helm_release"), "name")

    for name, spec in inventory["helm_releases"].items():
        expected = dict(spec["set_values"])
        expected["serviceAccount.create"] = "true"
        if spec["irsa_role"]:
            identity = spec["irsa_role"]
            expected["serviceAccount.name"] = inventory["irsa_roles"][identity][
                "service_account"
            ]
            expected[ROLE_ARN_ANNOTATION] = irsa_role_arn(inventory, identity)

        if name == LB_CONTROLLER:
            expected["clusterName"] = inventory["cluster_name"]
            expected["region"] = inventory["region"]
            expected["vpcId"] = inventory["vpc_id"]

        assert release_set_map(releases[name]) == expected, name


def test_trivy_runs_as_a_node_daemonset_on_every_worker(plan, inventory):
    """Trivy is the inventory node scanner: DaemonSet mode, all-node toleration, no selector."""
    assert TRIVY in inventory["helm_releases"]
    spec = inventory["helm_releases"][TRIVY]
    assert spec["irsa_role"] == ""
    assert spec["set_values"]["workloadKind"] == "DaemonSet"
    assert spec["set_values"]["trivy.mode"] == "Node"
    assert spec["set_values"]["tolerations[0].operator"] == "Exists"
    assert spec["set_values"]["tolerations[0].effect"] == ""
    assert not any(key.startswith("nodeSelector.") for key in spec["set_values"])

    releases = keyed(afters(plan, "helm_release"), "name")
    rendered = release_set_map(releases[TRIVY])
    assert rendered["workloadKind"] == "DaemonSet"
    assert rendered["trivy.mode"] == "Node"
    assert rendered["tolerations[0].operator"] == "Exists"
    assert rendered["tolerations[0].effect"] == ""
    assert ROLE_ARN_ANNOTATION not in rendered
    assert not any(key.startswith("nodeSelector.") for key in rendered)


def test_no_helm_value_is_marked_sensitive_or_hidden_from_review(plan):
    """Releases expose their configuration through plain set values only."""
    for planned in afters(plan, "helm_release"):
        assert not planned.get("set_sensitive"), planned["name"]
        assert not planned.get("values"), planned["name"]
