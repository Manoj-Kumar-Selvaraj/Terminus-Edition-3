"""The Artifactory credential helper, and the ban on literal registry credentials."""

from __future__ import annotations

import re

from conftest import afters, block, only

LITERAL_ENV_VARS = {"ARTIFACTORY_REGISTRY_URL", "ARTIFACTORY_REFRESH_INTERVAL_SECONDS"}
SECRET_NAME = re.compile(r"password|passwd|secret|token|credential", re.IGNORECASE)


def helper_container(plan):
    """The single container of the credential helper DaemonSet."""
    daemon_set = only(afters(plan, "kubernetes_daemon_set_v1"), "credential helper DaemonSet")
    pod_spec = block(block(block(daemon_set, "spec"), "template"), "spec")
    return daemon_set, pod_spec, only(pod_spec["container"], "helper container")


def test_credential_helper_runs_the_inventory_image_in_its_own_namespace(plan, inventory):
    """The DaemonSet name, namespace and image all come from the inventory."""
    artifactory = inventory["artifactory"]
    daemon_set, _, container = helper_container(plan)

    metadata = block(daemon_set, "metadata")
    assert metadata["name"] == artifactory["daemonset_name"]
    assert metadata["namespace"] == artifactory["namespace"]
    assert container["image"] == artifactory["helper_image"]


def test_helper_pods_pull_through_the_preprovisioned_secret(plan, inventory):
    """Image pulls are authenticated with the inventory pull secret."""
    artifactory = inventory["artifactory"]
    _, pod_spec, _ = helper_container(plan)

    pull_secrets = {entry["name"] for entry in pod_spec["image_pull_secrets"]}
    assert pull_secrets == {artifactory["pull_secret_name"]}


def test_registry_credential_is_injected_only_by_secret_key_reference(plan, inventory):
    """Username and password reach the container through secret key refs, not values."""
    artifactory = inventory["artifactory"]
    _, _, container = helper_container(plan)

    env = {entry["name"]: entry for entry in container["env"]}
    expected_keys = {
        "ARTIFACTORY_USERNAME": artifactory["username_secret_key"],
        "ARTIFACTORY_PASSWORD": artifactory["password_secret_key"],
    }
    assert LITERAL_ENV_VARS | set(expected_keys) == set(env), sorted(env)

    assert env["ARTIFACTORY_REGISTRY_URL"]["value"] == artifactory["registry_host"]
    assert env["ARTIFACTORY_REFRESH_INTERVAL_SECONDS"]["value"] == str(
        artifactory["refresh_interval_seconds"]
    )

    for name, secret_key in expected_keys.items():
        entry = env[name]
        assert not entry.get("value"), f"{name} must not carry a literal value"
        source = only(entry["value_from"], f"{name} value source")
        secret_ref = only(source["secret_key_ref"], f"{name} secret key ref")
        assert secret_ref["name"] == artifactory["pull_secret_name"], name
        assert secret_ref["key"] == secret_key, name


def test_the_module_never_materialises_the_pull_secret(plan, module_source):
    """The pull secret is referenced by name and never created by this module."""
    planned_types = {change["type"] for change in plan["resource_changes"]}
    assert not {t for t in planned_types if t.startswith("kubernetes_secret")}

    match = re.search(r'resource\s+"kubernetes_secret', module_source)
    assert match is None, "the module creates a Kubernetes secret"


def test_no_literal_registry_credential_survives_into_the_plan(plan, inventory):
    """No secret-shaped environment variable or Helm value holds a literal."""
    artifactory = inventory["artifactory"]
    allowed_literals = {
        artifactory["registry_host"],
        str(artifactory["refresh_interval_seconds"]),
    }

    literals = set()
    for change in plan["resource_changes"]:
        if change["type"] != "kubernetes_daemon_set_v1":
            continue
        pod_spec = block(block(block(change["change"]["after"], "spec"), "template"), "spec")
        for container in pod_spec["container"]:
            for entry in container["env"]:
                if entry.get("value"):
                    literals.add(entry["value"])
                if SECRET_NAME.search(entry["name"]):
                    assert not entry.get("value"), f"{entry['name']} carries a literal"
                    assert entry.get("value_from"), f"{entry['name']} has no secret source"

    assert literals == allowed_literals, sorted(literals)

    for release in afters(plan, "helm_release"):
        for entry in release["set"]:
            assert not SECRET_NAME.search(entry["name"]), (
                f"{release['name']} passes {entry['name']} as a plain Helm value"
            )
