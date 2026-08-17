import json
import pathlib
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
    injected = f"runner;touch${{IFS}}{sentinel};#"
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


def test_f2p_timeout_cleans_generated_playbook(tmp_path, cleanup_registry):
    """A timed-out Ansible process must fail safely and leave no generated playbook behind."""
    target = cleanup_registry.path(tmp_path / "managed-file")
    sleep_flag = tmp_path / "sleep.flag"
    sleep_flag.write_text("sleep", encoding="utf-8")
    wrapper = make_ansible_wrapper(tmp_path, sleep_flag=sleep_flag)
    temp_dir = tmp_path / "timeout-playbooks"
    workspace = make_workspace(
        tmp_path,
        f'''resource "ansibleops_file" "managed" {{
  path = {json.dumps(str(target))}
}}
''',
        ansible_binary=wrapper,
        timeout_seconds=1,
        temp_dir=temp_dir,
    )
    tf_apply(workspace, expect_success=False, timeout=20)
    leftovers = list(pathlib.Path(temp_dir).glob("ansibleops-*.yml")) if pathlib.Path(temp_dir).exists() else []
    assert leftovers == []


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
