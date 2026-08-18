import grp
import json
import os
import pathlib
import pwd

from conftest import (
    counter_value,
    make_ansible_wrapper,
    make_workspace,
    plan_actions,
    resource_values,
    rewrite_body,
    tf_apply,
    tf_destroy,
    tf_plan,
    tf_plan_json,
)


def test_f2p_filesystem_identities_survive_mutable_updates(tmp_path, cleanup_registry):
    """File/directory identity, backend use and equivalent mode spellings converge correctly."""
    file_path = cleanup_registry.path(tmp_path / "managed-file")
    directory = cleanup_registry.path(tmp_path / "managed-dir")
    runner_tmp = tmp_path / "runner"
    counter = tmp_path / "counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    body = f'''resource "ansibleops_file" "managed" {{
  path  = {json.dumps(str(file_path))}
  mode  = "0640"
  owner = "root"
  group = "root"
}}
resource "ansibleops_directory" "managed" {{
  path  = {json.dumps(str(directory))}
  mode  = "0750"
  owner = "root"
  group = "root"
}}
'''
    workspace = make_workspace(
        tmp_path,
        body,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_create = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) >= before_create + 2
    file_before = resource_values(workspace, "ansibleops_file.managed")["id"]
    directory_before = resource_values(workspace, "ansibleops_directory.managed")["id"]
    assert pathlib.Path(file_path).stat().st_uid == 0
    assert pathlib.Path(file_path).stat().st_gid == 0
    assert pathlib.Path(directory).stat().st_uid == 0
    assert pathlib.Path(directory).stat().st_gid == 0

    equivalent = body.replace('mode  = "0640"', 'mode  = "640"').replace(
        'mode  = "0750"', 'mode  = "750"'
    )
    rewrite_body(
        workspace,
        equivalent,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_equivalent_apply = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) == before_equivalent_apply
    before_clean_plan = counter_value(counter)
    assert tf_plan(workspace).returncode == 0
    assert counter_value(counter) == before_clean_plan

    updated = equivalent.replace('mode  = "640"', 'mode  = "0600"').replace(
        'mode  = "750"', 'mode  = "0700"'
    )
    rewrite_body(
        workspace,
        updated,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_update = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) >= before_update + 2
    assert resource_values(workspace, "ansibleops_file.managed")["id"] == file_before
    assert (
        resource_values(workspace, "ansibleops_directory.managed")["id"]
        == directory_before
    )

    before_delete = counter_value(counter)
    tf_destroy(workspace)
    assert counter_value(counter) >= before_delete + 2


def test_f2p_symlink_identity_survives_target_update(tmp_path, cleanup_registry):
    """Changing a symlink target is an in-place update and must preserve the link-path identity."""
    target1 = cleanup_registry.path(tmp_path / "target-one")
    target2 = cleanup_registry.path(tmp_path / "target-two")
    target1.write_text("one", encoding="utf-8")
    target2.write_text("two", encoding="utf-8")
    link = cleanup_registry.path(tmp_path / "managed-link")
    runner_tmp = tmp_path / "runner"
    body = f'''resource "ansibleops_symlink" "managed" {{
  path   = {json.dumps(str(link))}
  target = {json.dumps(str(target1))}
}}
'''
    workspace = make_workspace(tmp_path, body, temp_dir=runner_tmp)
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_symlink.managed")["id"]
    rewrite_body(workspace, body.replace(str(target1), str(target2)), temp_dir=runner_tmp)
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_symlink.managed")["id"]
    assert after == before
    assert os.readlink(link) == str(target2)


def test_f2p_deleted_directory_is_planned_for_recreation(tmp_path, cleanup_registry):
    """Refresh must recognize an externally deleted directory and plan to recreate it."""
    target = cleanup_registry.path(tmp_path / "deleted-dir")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
  mode = "0750"
}}
''',
    )
    tf_apply(workspace)
    pathlib.Path(target).rmdir()
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_directory.managed") == ["create"]


def test_f2p_filesystem_mode_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """Out-of-band mode and ownership drift must both plan in-place reconciliation."""
    file_path = cleanup_registry.path(tmp_path / "mode-file")
    directory = cleanup_registry.path(tmp_path / "mode-dir")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_file" "managed" {{
  path  = {json.dumps(str(file_path))}
  mode  = "0640"
  owner = "root"
  group = "root"
}}
resource "ansibleops_directory" "managed" {{
  path  = {json.dumps(str(directory))}
  mode  = "0750"
  owner = "root"
  group = "root"
}}
''',
    )
    tf_apply(workspace)
    nobody_uid = pwd.getpwnam("nobody").pw_uid
    nogroup_gid = grp.getgrnam("nogroup").gr_gid
    os.chmod(file_path, 0o666)
    os.chmod(directory, 0o777)
    os.chown(file_path, nobody_uid, nogroup_gid)
    os.chown(directory, nobody_uid, nogroup_gid)
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_file.managed") == ["update"]
    assert plan_actions(plan, "ansibleops_directory.managed") == ["update"]


def test_f2p_symlink_target_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """Refresh must readlink the owned path so an out-of-band target change is planned back to desired state."""
    target1 = cleanup_registry.path(tmp_path / "expected")
    target2 = cleanup_registry.path(tmp_path / "drifted")
    target1.write_text("one", encoding="utf-8")
    target2.write_text("two", encoding="utf-8")
    link = cleanup_registry.path(tmp_path / "link")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_symlink" "managed" {{
  path   = {json.dumps(str(link))}
  target = {json.dumps(str(target1))}
  force  = true
}}
''',
    )
    tf_apply(workspace)
    pathlib.Path(link).unlink()
    pathlib.Path(link).symlink_to(target2)
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_symlink.managed") == ["update"]


def test_f2p_wrong_object_kind_is_not_accepted_as_directory(tmp_path, cleanup_registry):
    """A regular file at a managed directory path is absence of the owned object, not a healthy directory."""
    target = cleanup_registry.path(tmp_path / "kind-path")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
    )
    tf_apply(workspace)
    pathlib.Path(target).rmdir()
    pathlib.Path(target).write_text("wrong kind", encoding="utf-8")
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_directory.managed") == ["create"]
