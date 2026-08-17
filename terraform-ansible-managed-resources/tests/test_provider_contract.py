import json
import pathlib

from conftest import make_workspace, resource_values, run, tf_apply, tf_destroy, tf_state_pull


def test_p2p_provider_exposes_exact_managed_resource_set(tmp_path):
    """The submitted binary remains a real Terraform provider exposing exactly the ten documented resources."""
    workspace = make_workspace(tmp_path, "")
    result = run(["terraform", "providers", "schema", "-json"], cwd=workspace)
    payload = json.loads(result.stdout)
    schema = payload["provider_schemas"]["registry.terraform.io/local/ansibleops"]
    assert set(schema["resource_schemas"]) == {
        "ansibleops_file",
        "ansibleops_directory",
        "ansibleops_copy",
        "ansibleops_template",
        "ansibleops_line",
        "ansibleops_block",
        "ansibleops_symlink",
        "ansibleops_user",
        "ansibleops_group",
        "ansibleops_cron",
    }


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
    """The provider persists resource data through Terraform state rather than a provider-owned side database."""
    target = cleanup_registry.path(tmp_path / "state-file")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_file" "state" {{
  path = {json.dumps(str(target))}
}}
''',
    )
    tf_apply(workspace)
    state = tf_state_pull(workspace)
    resources = state.get("resources", [])
    assert any(r.get("type") == "ansibleops_file" and r.get("name") == "state" for r in resources)
    assert not (pathlib.Path(workspace) / "state.db").exists()
    assert not (pathlib.Path(workspace) / "ansibleops-state.json").exists()
