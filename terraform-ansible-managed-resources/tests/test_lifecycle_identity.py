import json
import pathlib

from conftest import (
    make_workspace,
    plan_actions,
    resource_values,
    rewrite_body,
    run,
    tf_apply,
    tf_destroy,
    tf_plan_json,
    unique_unix_name,
)


def user_body(name, *, shell="/bin/sh", home=None, create_home=False, remove_home=False, groups=None):
    fields = [f'  name = {json.dumps(name)}', f'  shell = {json.dumps(shell)}']
    if home is not None:
        fields.append(f'  home = {json.dumps(str(home))}')
    fields.append(f'  create_home = {str(create_home).lower()}')
    fields.append(f'  remove_home_on_destroy = {str(remove_home).lower()}')
    if groups:
        fields.append("  groups = [" + ", ".join(json.dumps(g) for g in groups) + "]")
    return 'resource "ansibleops_user" "managed" {\n' + "\n".join(fields) + "\n}\n"


def test_f2p_user_identity_survives_shell_update(tmp_path, cleanup_registry):
    """A user name is the stable object key; mutable shell changes must preserve its Terraform identity."""
    name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    runner_tmp = tmp_path / "runner"
    workspace = make_workspace(tmp_path, user_body(name, shell="/bin/sh"), temp_dir=runner_tmp)
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_user.managed")["id"]
    rewrite_body(workspace, user_body(name, shell="/bin/bash"), temp_dir=runner_tmp)
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_user.managed")["id"]
    assert after == before


def test_f2p_user_shell_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """An out-of-band user shell change must refresh the configurable state and plan restoration."""
    name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    workspace = make_workspace(tmp_path, user_body(name, shell="/bin/sh"))
    tf_apply(workspace)
    run(["usermod", "-s", "/bin/bash", name])
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_user.managed") == ["update"]


def test_f2p_user_supplementary_group_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """Removing one configured supplementary group externally must produce an update for the managed user."""
    user = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    group1 = cleanup_registry.group(unique_unix_name("aopsg"))
    group2 = cleanup_registry.group(unique_unix_name("aopsg"))
    body = f'''resource "ansibleops_group" "one" {{
  name = {json.dumps(group1)}
}}
resource "ansibleops_group" "two" {{
  name = {json.dumps(group2)}
}}
resource "ansibleops_user" "managed" {{
  name        = {json.dumps(user)}
  groups      = [{json.dumps(group1)}, {json.dumps(group2)}]
  create_home = false
  depends_on  = [ansibleops_group.one, ansibleops_group.two]
}}
'''
    workspace = make_workspace(tmp_path, body)
    tf_apply(workspace)
    run(["gpasswd", "-d", user, group2])
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_user.managed") == ["update"]


def test_f2p_deleted_user_is_planned_for_recreation(tmp_path, cleanup_registry):
    """A user removed outside Terraform must disappear from refreshed state and be planned for recreation."""
    name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    workspace = make_workspace(tmp_path, user_body(name))
    tf_apply(workspace)
    run(["userdel", name])
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_user.managed") == ["create"]


def test_f2p_destroy_preserves_home_when_remove_home_is_false(tmp_path, cleanup_registry):
    """Destroying a user with remove_home_on_destroy=false must leave its home directory intact."""
    name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    home = cleanup_registry.path(tmp_path / "preserved-home")
    workspace = make_workspace(
        tmp_path,
        user_body(name, home=home, create_home=True, remove_home=False),
    )
    tf_apply(workspace)
    marker = pathlib.Path(home) / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    tf_destroy(workspace)
    assert pathlib.Path(home).is_dir()
    assert marker.read_text(encoding="utf-8") == "keep"


def test_f2p_destroy_removes_home_when_remove_home_is_true(tmp_path, cleanup_registry):
    """Destroying a user with remove_home_on_destroy=true must remove the managed user's home directory."""
    name = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    home = cleanup_registry.path(tmp_path / "removed-home")
    workspace = make_workspace(
        tmp_path,
        user_body(name, home=home, create_home=True, remove_home=True),
    )
    tf_apply(workspace)
    (pathlib.Path(home) / "remove.txt").write_text("remove", encoding="utf-8")
    tf_destroy(workspace)
    assert not pathlib.Path(home).exists()
