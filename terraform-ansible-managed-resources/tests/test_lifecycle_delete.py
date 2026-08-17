import json
import pathlib

from conftest import (
    make_ansible_wrapper,
    make_workspace,
    rewrite_body,
    run,
    state_has_resource,
    tf_apply,
    tf_destroy,
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


def test_f2p_symlink_destroy_preserves_target(tmp_path, cleanup_registry):
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
