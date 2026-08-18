import json
import pathlib

from conftest import (
    make_ansible_wrapper,
    make_workspace,
    resource_values,
    rewrite_body,
    run,
    state_has_resource,
    tf_apply,
    tf_destroy,
    unique_unix_name,
)


def test_f2p_failed_delete_preserves_managed_state_for_retry(tmp_path, cleanup_registry):
    """A failed Ansible teardown keeps both the external object and Terraform management so destroy can be retried."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    fail_flag = tmp_path / "fail.flag"
    wrapper = make_ansible_wrapper(tmp_path, fail_flag=fail_flag)
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        ansible_binary=wrapper,
    )
    tf_apply(workspace)
    assert pathlib.Path(target).is_dir()
    fail_flag.write_text("fail", encoding="utf-8")
    tf_destroy(workspace, expect_success=False)
    assert pathlib.Path(target).is_dir()
    assert state_has_resource(workspace, "ansibleops_directory.managed")
    fail_flag.unlink()
    tf_destroy(workspace)
    assert not pathlib.Path(target).exists()


def test_f2p_named_entry_deletes_preserve_siblings(tmp_path, cleanup_registry):
    """Removing one named line, block, and cron resource must leave sibling entries in their shared backing stores."""
    line_file = cleanup_registry.path(tmp_path / "lines.conf")
    block_file = cleanup_registry.path(tmp_path / "blocks.conf")
    cleanup_registry.cron("root")
    run(["crontab", "-u", "root", "-r"], check=False)

    line_one = f'''resource "ansibleops_line" "one" {{
  name   = "line-one"
  path   = {json.dumps(str(line_file))}
  line   = "line_one=true"
  create = true
}}
'''
    line_two = f'''resource "ansibleops_line" "two" {{
  name   = "line-two"
  path   = {json.dumps(str(line_file))}
  line   = "line_two=true"
  create = true
}}
'''
    block_one = f'''resource "ansibleops_block" "one" {{
  name   = "block-one"
  path   = {json.dumps(str(block_file))}
  block  = "block_one=true"
  create = true
}}
'''
    block_two = f'''resource "ansibleops_block" "two" {{
  name   = "block-two"
  path   = {json.dumps(str(block_file))}
  block  = "block_two=true"
  create = true
}}
'''
    cron_one = '''resource "ansibleops_cron" "one" {
  name = "cron-one"
  job  = "echo cron-one"
}
'''
    cron_two = '''resource "ansibleops_cron" "two" {
  name = "cron-two"
  job  = "echo cron-two"
}
'''

    workspace = make_workspace(tmp_path, line_one + block_one + cron_one)
    tf_apply(workspace)
    rewrite_body(workspace, line_one + line_two + block_one + block_two + cron_one + cron_two)
    tf_apply(workspace)
    line_two_id = resource_values(workspace, "ansibleops_line.two")["id"]
    block_two_id = resource_values(workspace, "ansibleops_block.two")["id"]
    cron_two_id = resource_values(workspace, "ansibleops_cron.two")["id"]
    rewrite_body(workspace, line_two + block_two + cron_two)
    tf_apply(workspace)

    line_text = pathlib.Path(line_file).read_text(encoding="utf-8")
    assert "line_one=true" not in line_text
    assert line_text.splitlines().count("line_two=true") == 1
    block_text = pathlib.Path(block_file).read_text(encoding="utf-8")
    assert "block_one=true" not in block_text
    assert "block_two=true" in block_text
    cron_text = run(["crontab", "-u", "root", "-l"]).stdout
    assert "#Ansible: cron-one" not in cron_text
    assert "echo cron-one" not in cron_text
    assert "#Ansible: cron-two" in cron_text
    assert "echo cron-two" in cron_text
    assert resource_values(workspace, "ansibleops_line.two")["id"] == line_two_id
    assert resource_values(workspace, "ansibleops_block.two")["id"] == block_two_id
    assert resource_values(workspace, "ansibleops_cron.two")["id"] == cron_two_id


def test_p2p_symlink_destroy_preserves_target(tmp_path, cleanup_registry):
    """Destroying a managed symlink removes the link path only and leaves the target file untouched."""
    target = cleanup_registry.path(tmp_path / "target.txt")
    target.write_text("keep-target\n", encoding="utf-8")
    link = cleanup_registry.path(tmp_path / "managed-link")
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_symlink" "managed" {{
  path   = {json.dumps(str(link))}
  target = {json.dumps(str(target))}
}}
''',
    )
    tf_apply(workspace)
    assert pathlib.Path(link).is_symlink()
    tf_destroy(workspace)
    assert not pathlib.Path(link).exists()
    assert pathlib.Path(target).read_text(encoding="utf-8") == "keep-target\n"


def test_p2p_destroy_succeeds_when_owned_object_is_already_absent(tmp_path, cleanup_registry):
    """Destroy succeeds after external absence for filesystem, account, and cron ownership classes."""
    directory = cleanup_registry.path(tmp_path / "already-gone-dir")
    directory_root = tmp_path / "directory-case"
    directory_workspace = make_workspace(
        directory_root,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(directory))}
}}
''',
    )
    tf_apply(directory_workspace)
    pathlib.Path(directory).rmdir()
    tf_destroy(directory_workspace)
    assert not state_has_resource(directory_workspace, "ansibleops_directory.managed")

    user = cleanup_registry.user(unique_unix_name("aopsu"), remove_home=False)
    user_root = tmp_path / "user-case"
    user_workspace = make_workspace(
        user_root,
        f'''resource "ansibleops_user" "managed" {{
  name        = {json.dumps(user)}
  create_home = false
}}
''',
    )
    tf_apply(user_workspace)
    run(["userdel", user])
    tf_destroy(user_workspace)
    assert not state_has_resource(user_workspace, "ansibleops_user.managed")

    cleanup_registry.cron("root")
    run(["crontab", "-u", "root", "-r"], check=False)
    cron_root = tmp_path / "cron-case"
    cron_workspace = make_workspace(
        cron_root,
        '''resource "ansibleops_cron" "managed" {
  name = "already-gone"
  job  = "echo gone"
}
''',
    )
    tf_apply(cron_workspace)
    run(["crontab", "-u", "root", "-r"], check=False)
    tf_destroy(cron_workspace)
    assert not state_has_resource(cron_workspace, "ansibleops_cron.managed")
