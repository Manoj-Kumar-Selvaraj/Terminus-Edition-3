import json
import pathlib
import signal
import subprocess
import time

from conftest import (
    make_ansible_wrapper,
    make_workspace,
    resource_values,
    rewrite_body,
    state_has_resource,
    tf_apply,
)


def test_f2p_line_and_block_duplicate_external_ownership_is_rejected(tmp_path, cleanup_registry):
    """Named line/block resources reject duplicate path+name ownership keys."""
    line_path = cleanup_registry.path(tmp_path / "owned-lines.txt")
    line_path.write_text("seed\n", encoding="utf-8")
    line_workspace = make_workspace(
        tmp_path / "line-collision",
        f'''resource "ansibleops_line" "one" {{
  name = "shared-line"
  path = {json.dumps(str(line_path))}
  line = "one"
}}
resource "ansibleops_line" "two" {{
  name = "shared-line"
  path = {json.dumps(str(line_path))}
  line = "two"
}}
''',
    )
    tf_apply(line_workspace, expect_success=False)
    assert line_path.read_text(encoding="utf-8") == "seed\n"

    block_path = cleanup_registry.path(tmp_path / "owned-blocks.txt")
    block_path.write_text("seed\n", encoding="utf-8")
    block_workspace = make_workspace(
        tmp_path / "block-collision",
        f'''resource "ansibleops_block" "one" {{
  name  = "shared-block"
  path  = {json.dumps(str(block_path))}
  block = "one"
}}
resource "ansibleops_block" "two" {{
  name  = "shared-block"
  path  = {json.dumps(str(block_path))}
  block = "two"
}}
''',
    )
    tf_apply(block_workspace, expect_success=False)
    assert block_path.read_text(encoding="utf-8") == "seed\n"


def test_f2p_timeout_and_cancellation_preserve_last_successful_update_state(tmp_path, cleanup_registry):
    """A timed-out or cancelled update preserves external state and the last successful Terraform state."""
    timeout_root = tmp_path / "timeout-update"
    timeout_target = cleanup_registry.path(tmp_path / "timeout-update-file")
    timeout_sleep = timeout_root / "sleep.flag"
    timeout_wrapper = make_ansible_wrapper(timeout_root, sleep_flag=timeout_sleep)
    timeout_temp = timeout_root / "playbooks"
    timeout_initial = f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(timeout_target))}
  mode = "0640"
}}
'''
    timeout_workspace = make_workspace(
        timeout_root,
        timeout_initial,
        ansible_binary=timeout_wrapper,
        timeout_seconds=1,
        temp_dir=timeout_temp,
    )
    tf_apply(timeout_workspace)
    timeout_before = resource_values(timeout_workspace, "ansibleops_file.managed")
    assert pathlib.Path(timeout_target).stat().st_mode & 0o777 == 0o640

    timeout_sleep.write_text("sleep", encoding="utf-8")
    rewrite_body(
        timeout_workspace,
        timeout_initial.replace('mode = "0640"', 'mode = "0600"'),
        ansible_binary=timeout_wrapper,
        timeout_seconds=1,
        temp_dir=timeout_temp,
    )
    tf_apply(timeout_workspace, expect_success=False, timeout=20)
    timeout_after = resource_values(timeout_workspace, "ansibleops_file.managed")
    assert timeout_after["id"] == timeout_before["id"]
    assert timeout_after["mode"] == timeout_before["mode"]
    assert pathlib.Path(timeout_target).stat().st_mode & 0o777 == 0o640
    assert list(timeout_temp.glob("ansibleops-*.yml")) == []

    cancel_root = tmp_path / "cancel-update"
    cancel_target = cleanup_registry.path(tmp_path / "cancel-update-file")
    cancel_sleep = cancel_root / "sleep.flag"
    cancel_wrapper = make_ansible_wrapper(cancel_root, sleep_flag=cancel_sleep)
    cancel_temp = cancel_root / "playbooks"
    cancel_initial = f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(cancel_target))}
  mode = "0640"
}}
'''
    cancel_workspace = make_workspace(
        cancel_root,
        cancel_initial,
        ansible_binary=cancel_wrapper,
        timeout_seconds=20,
        temp_dir=cancel_temp,
    )
    tf_apply(cancel_workspace)
    cancel_before = resource_values(cancel_workspace, "ansibleops_file.managed")
    assert pathlib.Path(cancel_target).stat().st_mode & 0o777 == 0o640

    cancel_sleep.write_text("sleep", encoding="utf-8")
    rewrite_body(
        cancel_workspace,
        cancel_initial.replace('mode = "0640"', 'mode = "0600"'),
        ansible_binary=cancel_wrapper,
        timeout_seconds=20,
        temp_dir=cancel_temp,
    )
    process = subprocess.Popen(
        ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
        cwd=cancel_workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        if cancel_temp.exists() and list(cancel_temp.glob("ansibleops-*.yml")):
            break
        if process.poll() is not None:
            break
        time.sleep(0.1)
    assert process.poll() is None, "terraform update exited before cancellation could be exercised"
    process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        raise AssertionError(f"terraform update did not stop after cancellation:\n{stdout}\n{stderr}")
    assert process.returncode != 0
    assert state_has_resource(cancel_workspace, "ansibleops_file.managed")
    cancel_after = resource_values(cancel_workspace, "ansibleops_file.managed")
    assert cancel_after["id"] == cancel_before["id"]
    assert cancel_after["mode"] == cancel_before["mode"]
    assert pathlib.Path(cancel_target).stat().st_mode & 0o777 == 0o640
    assert list(cancel_temp.glob("ansibleops-*.yml")) == []
