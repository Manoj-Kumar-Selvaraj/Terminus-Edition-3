import json
import pathlib
import signal
import subprocess
import time
import uuid

from conftest import (
    counter_value,
    make_ansible_wrapper,
    make_workspace,
    plan_actions,
    resource_values,
    rewrite_body,
    run,
    state_has_resource,
    tf_apply,
    tf_destroy,
    tf_plan,
    tf_plan_json,
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


def test_p2p_success_cleanup_and_state_output_secrecy(tmp_path, cleanup_registry):
    """Successful mutations clean generated playbooks and do not persist Ansible command output in Terraform state."""
    target = cleanup_registry.path(tmp_path / "success-directory")
    temp_dir = tmp_path / "success-playbooks"
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        temp_dir=temp_dir,
    )
    tf_apply(workspace)
    leftovers = list(temp_dir.glob("ansibleops-*.yml")) if temp_dir.exists() else []
    assert leftovers == []
    values = resource_values(workspace, "ansibleops_directory.managed")
    forbidden = {
        "stdout",
        "stderr",
        "command",
        "command_output",
        "ansible_output",
        "playbook",
        "playbook_path",
    }
    assert forbidden.isdisjoint(values)
    rendered_state = json.dumps(values, sort_keys=True)
    assert "PLAY [" not in rendered_state
    assert "TASK [" not in rendered_state
    tf_destroy(workspace)
    leftovers = list(temp_dir.glob("ansibleops-*.yml")) if temp_dir.exists() else []
    assert leftovers == []


def test_f2p_nonzero_ansible_exit_fails_lifecycle_transition(tmp_path, cleanup_registry):
    """A non-zero Ansible exit fails the transition, preserves state truth, and cleans the generated playbook."""
    target = cleanup_registry.path(tmp_path / "managed-dir")
    fail_flag = tmp_path / "fail.flag"
    fail_flag.write_text("fail", encoding="utf-8")
    wrapper = make_ansible_wrapper(tmp_path, fail_flag=fail_flag)
    temp_dir = tmp_path / "failure-playbooks"
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_directory" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        ansible_binary=wrapper,
        temp_dir=temp_dir,
    )
    tf_apply(workspace, expect_success=False)
    assert not pathlib.Path(target).exists()
    assert not state_has_resource(workspace, "ansibleops_directory.managed")
    leftovers = list(temp_dir.glob("ansibleops-*.yml")) if temp_dir.exists() else []
    assert leftovers == []


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
    """Cron defaults, backend use, drift, absent destroy and mutable updates converge with stable identity."""
    cleanup_registry.cron("root")
    run(["crontab", "-u", "root", "-r"], check=False)
    name = "ansibleops-defaults"
    runner_tmp = tmp_path / "runner"
    counter = tmp_path / "cron-counter.log"
    wrapper = make_ansible_wrapper(tmp_path, counter=counter)
    omitted = f'''resource "ansibleops_cron" "managed" {{
  name = {json.dumps(name)}
  job  = "echo ansibleops-defaults"
}}
'''
    workspace = make_workspace(
        tmp_path,
        omitted,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_create = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) >= before_create + 1
    before_id = resource_values(workspace, "ansibleops_cron.managed")["id"]
    listing = run(["crontab", "-u", "root", "-l"]).stdout
    assert f"#Ansible: {name}" in listing
    assert "* * * * * echo ansibleops-defaults" in listing
    before_clean_plan = counter_value(counter)
    plan = tf_plan(workspace)
    assert plan.returncode == 0
    assert counter_value(counter) == before_clean_plan

    explicit = f'''resource "ansibleops_cron" "managed" {{
  name    = {json.dumps(name)}
  user    = "root"
  minute  = "*"
  hour    = "*"
  day     = "*"
  month   = "*"
  weekday = "*"
  job     = "echo ansibleops-defaults"
}}
'''
    rewrite_body(
        workspace,
        explicit,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_equivalent_apply = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) == before_equivalent_apply
    before_equivalent_plan = counter_value(counter)
    assert tf_plan(workspace).returncode == 0
    assert counter_value(counter) == before_equivalent_plan

    drifted = listing.replace("echo ansibleops-defaults", "echo drifted")
    drift_file = tmp_path / "drift.cron"
    drift_file.write_text(drifted, encoding="utf-8")
    run(["crontab", "-u", "root", str(drift_file)])
    before_drift_plan = counter_value(counter)
    _, drift_plan = tf_plan_json(workspace)
    assert plan_actions(drift_plan, "ansibleops_cron.managed") == ["update"]
    assert counter_value(counter) == before_drift_plan

    updated = explicit.replace('hour    = "*"', 'hour    = "1"').replace(
        'job     = "echo ansibleops-defaults"', 'job     = "echo updated"'
    )
    rewrite_body(
        workspace,
        updated,
        ansible_binary=wrapper,
        temp_dir=runner_tmp,
    )
    before_update = counter_value(counter)
    tf_apply(workspace)
    assert counter_value(counter) >= before_update + 1
    assert resource_values(workspace, "ansibleops_cron.managed")["id"] == before_id
    final_listing = run(["crontab", "-u", "root", "-l"]).stdout
    assert "* 1 * * * echo updated" in final_listing

    run(["crontab", "-u", "root", "-r"], check=False)
    tf_destroy(workspace)
    assert not state_has_resource(workspace, "ansibleops_cron.managed")
