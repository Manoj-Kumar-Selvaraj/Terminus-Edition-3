import json
import os
import pathlib

from conftest import (
    make_workspace,
    plan_actions,
    resource_values,
    rewrite_body,
    tf_apply,
    tf_plan_json,
)


def test_f2p_file_identity_survives_metadata_update(tmp_path, cleanup_registry):
    """Changing mutable file metadata must not change the Terraform resource identity."""
    target = cleanup_registry.path(tmp_path / "managed-file")
    runner_tmp = tmp_path / "runner"
    body = f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(target))}
  mode = "0640"
}}
'''
    workspace = make_workspace(tmp_path, body, temp_dir=runner_tmp)
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_file.managed")["id"]
    rewrite_body(
        workspace,
        body.replace('mode = "0640"', 'mode = "0600"'),
        temp_dir=runner_tmp,
    )
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_file.managed")["id"]
    assert after == before


def test_f2p_directory_identity_survives_mode_update(tmp_path, cleanup_registry):
    """A directory keeps one stable identity while its managed mode changes in place."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    runner_tmp = tmp_path / "runner"
    body = f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
  mode = "0750"
}}
'''
    workspace = make_workspace(tmp_path, body, temp_dir=runner_tmp)
    tf_apply(workspace)
    before = resource_values(workspace, "ansibleops_directory.managed")["id"]
    rewrite_body(workspace, body.replace('mode = "0750"', 'mode = "0700"'), temp_dir=runner_tmp)
    tf_apply(workspace)
    after = resource_values(workspace, "ansibleops_directory.managed")["id"]
    assert after == before


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


def test_f2p_directory_mode_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """Out-of-band directory permission drift must produce an in-place reconciliation action."""
    target = cleanup_registry.path(tmp_path / "mode-dir")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
  mode = "0750"
}}
''',
    )
    tf_apply(workspace)
    os.chmod(target, 0o777)
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_directory.managed") == ["update"]


def test_f2p_file_mode_drift_requires_reconciliation(tmp_path, cleanup_registry):
    """Out-of-band file permission drift must update the managed file instead of only a computed observation field."""
    target = cleanup_registry.path(tmp_path / "mode-file")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(target))}
  mode = "0640"
}}
''',
    )
    tf_apply(workspace)
    os.chmod(target, 0o666)
    _, plan = tf_plan_json(workspace)
    assert plan_actions(plan, "ansibleops_file.managed") == ["update"]


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
