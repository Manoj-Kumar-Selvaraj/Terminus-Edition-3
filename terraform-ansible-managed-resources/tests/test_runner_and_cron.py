import json
import pathlib
import signal
import subprocess
import time
import uuid

from conftest import (
    make_ansible_wrapper,
    make_workspace,
    run,
    state_has_resource,
    tf_apply,
    tf_plan,
)


def test_f2p_runner_handles_temp_paths_with_spaces(tmp_path, cleanup_registry):
    """A valid temporary-playbook directory containing spaces must be passed as data, not shell-split text."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    temp_dir = tmp_path / "runner temp with spaces"
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        temp_dir=temp_dir,
    )
    tf_apply(workspace)
    assert pathlib.Path(target).is_dir()


def test_f2p_runner_does_not_interpret_shell_metacharacters(tmp_path, cleanup_registry):
    """Shell metacharacters embedded in an otherwise valid temp path must remain literal and never execute commands."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    sentinel = cleanup_registry.path(pathlib.Path("/tmp") / f"ansibleops-injected-{uuid.uuid4().hex[:8]}")
    injected = f"runner;touch$IFS{sentinel};#"
    temp_dir = tmp_path / injected
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        temp_dir=temp_dir,
    )
    tf_apply(workspace)
    assert pathlib.Path(target).is_dir()
    assert not pathlib.Path(sentinel).exists()


def test_f2p_nonzero_ansible_exit_fails_lifecycle_transition(tmp_path, cleanup_registry):
    """A non-zero ansible-playbook exit must fail apply and must not publish a resource that was never created."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    fail_flag = tmp_path / "fail.flag"
    fail_flag.write_text("fail", encoding="utf-8")
    wrapper = make_ansible_wrapper(tmp_path, fail_flag=fail_flag)
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        ansible_binary=wrapper,
    )
    tf_apply(workspace, expect_success=False)
    assert not pathlib.Path(target).exists()
    assert not state_has_resource(workspace, "ansibleops_directory.managed")


def test_f2p_timeout_and_cancellation_clean_generated_playbooks(tmp_path, cleanup_registry):
    """Timeout and Terraform cancellation both fail safely and remove their generated Ansible playbooks."""
    timeout_root = tmp_path / "timeout-case"
    timeout_target = cleanup_registry.path(tmp_path / "timeout-file")
    timeout_sleep = timeout_root / "sleep.flag"
    timeout_sleep.parent.mkdir(parents=True, exist_ok=True)
    timeout_sleep.write_text("sleep", encoding="utf-8")
    timeout_wrapper = make_ansible_wrapper(timeout_root, sleep_flag=timeout_sleep)
    timeout_temp = timeout_root / "playbooks"
    timeout_workspace = make_workspace(
        timeout_root,
        f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(timeout_target))}
}}
''',
        ansible_binary=timeout_wrapper,
        timeout_seconds=1,
        temp_dir=timeout_temp,
    )
    tf_apply(timeout_workspace, expect_success=False, timeout=20)
    timeout_leftovers = list(timeout_temp.glob("ansibleops-*.yml")) if timeout_temp.exists() else []
    assert timeout_leftovers == []

    cancel_root = tmp_path / "cancel-case"
    cancel_target = cleanup_registry.path(tmp_path / "cancel-file")
    cancel_sleep = cancel_root / "sleep.flag"
    cancel_sleep.parent.mkdir(parents=True, exist_ok=True)
    cancel_sleep.write_text("sleep", encoding="utf-8")
    cancel_wrapper = make_ansible_wrapper(cancel_root, sleep_flag=cancel_sleep)
    cancel_temp = cancel_root / "playbooks"
    cancel_workspace = make_workspace(
        cancel_root,
        f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(cancel_target))}
}}
''',
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
    assert process.poll() is None, "terraform apply exited before cancellation could be exercised"
    process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        raise AssertionError(f"terraform apply did not stop after cancellation:\n{stdout}\n{stderr}")
    assert process.returncode != 0
    cancel_leftovers = list(cancel_temp.glob("ansibleops-*.yml")) if cancel_temp.exists() else []
    assert cancel_leftovers == []
    assert not state_has_resource(cancel_workspace, "ansibleops_file.managed")


def test_f2p_cron_omitted_schedule_fields_converge_to_wildcards(tmp_path, cleanup_registry):
    """Omitted cron user/schedule fields must mean root and wildcard defaults and remain clean on the next plan."""
    cleanup_registry.cron("root")
    run(["crontab", "-u", "root", "-r"], check=False)
    name = "ansibleops-defaults"
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_cron" "managed" {{
  name = {json.dumps(name)}
  job  = "echo ansibleops-defaults"
}}
''',
    )
    tf_apply(workspace)
    listing = run(["crontab", "-u", "root", "-l"]).stdout
    assert f"#Ansible: {name}" in listing
    assert "* * * * * echo ansibleops-defaults" in listing
    plan = tf_plan(workspace)
    assert plan.returncode == 0
