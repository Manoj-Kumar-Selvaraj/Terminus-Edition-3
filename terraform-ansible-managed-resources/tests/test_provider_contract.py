import json
import pathlib

from conftest import (
    PROVIDER_ROOT,
    make_workspace,
    resource_values,
    run,
    tf_apply,
    tf_destroy,
    tf_state_pull,
    unique_unix_name,
)


STRING = "string"
NUMBER = "number"
BOOL = "bool"
LIST_STRING = ["list", "string"]
MAP_STRING = ["map", "string"]


def attr(type_, *, required=False, optional=False, computed=False):
    return {
        "type": type_,
        "required": required,
        "optional": optional,
        "computed": computed,
    }


EXPECTED_RESOURCE_SCHEMAS = {
    "ansibleops_file": {
        "id": attr(STRING, computed=True),
        "path": attr(STRING, required=True),
        "mode": attr(STRING, optional=True),
        "owner": attr(STRING, optional=True),
        "group": attr(STRING, optional=True),
        "observed_mode": attr(STRING, computed=True),
        "observed_owner": attr(STRING, computed=True),
        "observed_group": attr(STRING, computed=True),
    },
    "ansibleops_directory": {
        "id": attr(STRING, computed=True),
        "path": attr(STRING, required=True),
        "mode": attr(STRING, optional=True),
        "owner": attr(STRING, optional=True),
        "group": attr(STRING, optional=True),
        "observed_kind": attr(STRING, computed=True),
        "observed_mode": attr(STRING, computed=True),
        "observed_owner": attr(STRING, computed=True),
        "observed_group": attr(STRING, computed=True),
    },
    "ansibleops_copy": {
        "id": attr(STRING, computed=True),
        "source": attr(STRING, required=True),
        "source_digest": attr(STRING, required=True),
        "destination": attr(STRING, required=True),
        "mode": attr(STRING, optional=True),
        "owner": attr(STRING, optional=True),
        "group": attr(STRING, optional=True),
        "destination_digest": attr(STRING, computed=True),
        "observed_mode": attr(STRING, computed=True),
    },
    "ansibleops_template": {
        "id": attr(STRING, computed=True),
        "source": attr(STRING, required=True),
        "source_digest": attr(STRING, required=True),
        "destination": attr(STRING, required=True),
        "mode": attr(STRING, optional=True),
        "owner": attr(STRING, optional=True),
        "group": attr(STRING, optional=True),
        "variables": attr(MAP_STRING, optional=True),
        "variables_fingerprint": attr(STRING, computed=True),
        "destination_digest": attr(STRING, computed=True),
    },
    "ansibleops_line": {
        "id": attr(STRING, computed=True),
        "name": attr(STRING, required=True),
        "path": attr(STRING, required=True),
        "line": attr(STRING, required=True),
        "regexp": attr(STRING, optional=True),
        "create": attr(BOOL, optional=True),
        "observed_exact_count": attr(NUMBER, computed=True),
        "observed_regexp_count": attr(NUMBER, computed=True),
    },
    "ansibleops_block": {
        "id": attr(STRING, computed=True),
        "name": attr(STRING, required=True),
        "path": attr(STRING, required=True),
        "block": attr(STRING, required=True),
        "marker": attr(STRING, optional=True, computed=True),
        "create": attr(BOOL, optional=True),
        "observed": attr(BOOL, computed=True),
    },
    "ansibleops_symlink": {
        "id": attr(STRING, computed=True),
        "path": attr(STRING, required=True),
        "target": attr(STRING, required=True),
        "force": attr(BOOL, optional=True),
        "observed_target": attr(STRING, computed=True),
        "observed_kind": attr(STRING, computed=True),
    },
    "ansibleops_user": {
        "id": attr(STRING, computed=True),
        "name": attr(STRING, required=True),
        "uid": attr(NUMBER, optional=True),
        "group": attr(STRING, optional=True),
        "groups": attr(LIST_STRING, optional=True),
        "shell": attr(STRING, optional=True),
        "home": attr(STRING, optional=True),
        "create_home": attr(BOOL, optional=True),
        "remove_home_on_destroy": attr(BOOL, optional=True),
        "observed_uid": attr(NUMBER, computed=True),
        "observed_gid": attr(NUMBER, computed=True),
        "observed_group": attr(STRING, computed=True),
        "observed_groups": attr(LIST_STRING, computed=True),
        "observed_shell": attr(STRING, computed=True),
        "observed_home": attr(STRING, computed=True),
    },
    "ansibleops_group": {
        "id": attr(STRING, computed=True),
        "name": attr(STRING, required=True),
        "gid": attr(NUMBER, optional=True),
        "system": attr(BOOL, optional=True),
        "observed_gid": attr(NUMBER, computed=True),
        "observed_members": attr(LIST_STRING, computed=True),
    },
    "ansibleops_cron": {
        "id": attr(STRING, computed=True),
        "name": attr(STRING, required=True),
        "user": attr(STRING, optional=True),
        "minute": attr(STRING, optional=True),
        "hour": attr(STRING, optional=True),
        "day": attr(STRING, optional=True),
        "month": attr(STRING, optional=True),
        "weekday": attr(STRING, optional=True),
        "job": attr(STRING, required=True),
        "disabled": attr(BOOL, optional=True),
        "observed_minute": attr(STRING, computed=True),
        "observed_hour": attr(STRING, computed=True),
        "observed_day": attr(STRING, computed=True),
        "observed_month": attr(STRING, computed=True),
        "observed_weekday": attr(STRING, computed=True),
        "observed_job": attr(STRING, computed=True),
        "observed_disabled": attr(BOOL, computed=True),
    },
}


def test_f2p_provider_exposes_exact_managed_resource_schemas(tmp_path):
    """All ten public resources retain their documented Terraform attribute types and roles."""
    workspace = make_workspace(tmp_path, "")
    result = run(["terraform", "providers", "schema", "-json"], cwd=workspace)
    payload = json.loads(result.stdout)
    provider = payload["provider_schemas"]["registry.terraform.io/local/ansibleops"]
    resources = provider["resource_schemas"]
    assert set(resources) == set(EXPECTED_RESOURCE_SCHEMAS)
    for resource_name, expected in EXPECTED_RESOURCE_SCHEMAS.items():
        actual = resources[resource_name]["block"]["attributes"]
        assert set(actual) == set(expected), resource_name
        for name, expected_attr in expected.items():
            actual_attr = actual[name]
            shape = {
                "type": actual_attr["type"],
                "required": bool(actual_attr.get("required", False)),
                "optional": bool(actual_attr.get("optional", False)),
                "computed": bool(actual_attr.get("computed", False)),
            }
            assert shape == expected_attr, f"{resource_name}.{name}"


def test_p2p_directory_basic_apply_state_and_destroy(tmp_path, cleanup_registry):
    """A basic directory resource is created through Terraform, stored in real state, and removed on destroy."""
    target = cleanup_registry.path(tmp_path / "managed-directory")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "basic" {{
  path = {json.dumps(str(target))}
  mode = "0750"
}}
''',
    )
    tf_apply(workspace)
    assert pathlib.Path(target).is_dir()
    values = resource_values(workspace, "ansibleops_directory.basic")
    assert values["path"] == str(target)
    assert values["id"]
    state = tf_state_pull(workspace)
    assert state["version"] == 4
    assert state["serial"] >= 1
    tf_destroy(workspace)
    assert not pathlib.Path(target).exists()


def test_p2p_state_is_owned_by_terraform_core(tmp_path, cleanup_registry):
    """Provider execution leaves durable resource state only in Terraform Core's files."""
    target = cleanup_registry.path(tmp_path / "state-file")
    temp_dir = tmp_path / "provider-runtime"
    provider_files_before = {
        path.relative_to(PROVIDER_ROOT)
        for path in PROVIDER_ROOT.rglob("*")
        if path.is_file() and "vendor" not in path.relative_to(PROVIDER_ROOT).parts
    }
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_file" "state" {{
  path = {json.dumps(str(target))}
}}
''',
        temp_dir=temp_dir,
    )
    tf_apply(workspace)
    state = tf_state_pull(workspace)
    resources = state.get("resources", [])
    assert any(r.get("type") == "ansibleops_file" and r.get("name") == "state" for r in resources)
    tf_destroy(workspace)

    provider_files_after = {
        path.relative_to(PROVIDER_ROOT)
        for path in PROVIDER_ROOT.rglob("*")
        if path.is_file() and "vendor" not in path.relative_to(PROVIDER_ROOT).parts
    }
    assert provider_files_after == provider_files_before
    runtime_files = [path for path in temp_dir.rglob("*") if path.is_file()] if temp_dir.exists() else []
    assert runtime_files == []

    allowed_workspace = {
        pathlib.Path("main.tf"),
        pathlib.Path(".terraform.lock.hcl"),
        pathlib.Path("terraform.tfstate"),
        pathlib.Path("terraform.tfstate.backup"),
    }
    unexpected = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        if rel.parts and rel.parts[0] == ".terraform":
            continue
        if rel not in allowed_workspace:
            unexpected.append(rel)
    assert unexpected == []


def test_f2p_duplicate_external_ownership_is_rejected(tmp_path, cleanup_registry):
    """Two Terraform resources cannot simultaneously claim the same external object key."""
    shared_path = cleanup_registry.path(tmp_path / "shared-file")
    path_root = tmp_path / "path-collision"
    path_workspace = make_workspace(
        path_root,
        f'''resource "ansibleops_file" "one" {{
  path = {json.dumps(str(shared_path))}
}}
resource "ansibleops_file" "two" {{
  path = {json.dumps(str(shared_path))}
}}
''',
    )
    tf_apply(path_workspace, expect_success=False)

    user_name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    user_root = tmp_path / "user-collision"
    user_workspace = make_workspace(
        user_root,
        f'''resource "ansibleops_user" "one" {{
  name = {json.dumps(user_name)}
  create_home = false
}}
resource "ansibleops_user" "two" {{
  name = {json.dumps(user_name)}
  create_home = false
}}
''',
    )
    tf_apply(user_workspace, expect_success=False)

    group_name = cleanup_registry.group(unique_unix_name("aopsg"))
    group_root = tmp_path / "group-collision"
    group_workspace = make_workspace(
        group_root,
        f'''resource "ansibleops_group" "one" {{
  name = {json.dumps(group_name)}
}}
resource "ansibleops_group" "two" {{
  name = {json.dumps(group_name)}
}}
''',
    )
    tf_apply(group_workspace, expect_success=False)

    cleanup_registry.cron("root")
    run(["crontab", "-u", "root", "-r"], check=False)
    cron_root = tmp_path / "cron-collision"
    cron_workspace = make_workspace(
        cron_root,
        '''resource "ansibleops_cron" "one" {
  name = "same-entry"
  job  = "echo one"
}
resource "ansibleops_cron" "two" {
  name = "same-entry"
  job  = "echo two"
}
''',
    )
    tf_apply(cron_workspace, expect_success=False)
