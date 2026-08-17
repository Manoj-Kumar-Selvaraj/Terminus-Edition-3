import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import uuid

import pytest

PROVIDER_ROOT = pathlib.Path(os.environ.get("ANSIBLEOPS_ROOT", "/app/provider"))
INVENTORY = PROVIDER_ROOT / "config" / "inventory.ini"
REAL_ANSIBLE = shutil.which("ansible-playbook") or "/usr/bin/ansible-playbook"


def run(command, *, cwd=None, env=None, check=True, timeout=90):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(map(str, command))}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def hcl_string(value):
    return json.dumps(str(value))


def provider_config(*, ansible_binary=REAL_ANSIBLE, timeout_seconds=15, temp_dir="/tmp/ansibleops"):
    return f'''terraform {{
  required_providers {{
    ansibleops = {{
      source  = "local/ansibleops"
      version = "0.1.0"
    }}
  }}
}}

provider "ansibleops" {{
  inventory       = {hcl_string(INVENTORY)}
  ansible_binary  = {hcl_string(ansible_binary)}
  timeout_seconds = {int(timeout_seconds)}
  temp_dir        = {hcl_string(temp_dir)}
}}
'''


def make_workspace(tmp_path, body, *, ansible_binary=REAL_ANSIBLE, timeout_seconds=15, temp_dir=None):
    workspace = tmp_path / "tf"
    workspace.mkdir(parents=True, exist_ok=True)
    if temp_dir is None:
        temp_dir = tmp_path / "runner-tmp"
    main = workspace / "main.tf"
    main.write_text(
        provider_config(
            ansible_binary=ansible_binary,
            timeout_seconds=timeout_seconds,
            temp_dir=temp_dir,
        )
        + "\n"
        + body,
        encoding="utf-8",
    )
    run(["terraform", "init", "-input=false", "-no-color"], cwd=workspace)
    return workspace


def rewrite_body(workspace, body, *, ansible_binary=REAL_ANSIBLE, timeout_seconds=15, temp_dir="/tmp/ansibleops"):
    (pathlib.Path(workspace) / "main.tf").write_text(
        provider_config(
            ansible_binary=ansible_binary,
            timeout_seconds=timeout_seconds,
            temp_dir=temp_dir,
        )
        + "\n"
        + body,
        encoding="utf-8",
    )


def tf_apply(workspace, *, expect_success=True, timeout=120):
    result = run(
        ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
        cwd=workspace,
        check=False,
        timeout=timeout,
    )
    if expect_success and result.returncode != 0:
        raise AssertionError(f"terraform apply failed:\n{result.stdout}\n{result.stderr}")
    if not expect_success and result.returncode == 0:
        raise AssertionError("terraform apply unexpectedly succeeded")
    return result


def tf_destroy(workspace, *, expect_success=True, timeout=120):
    result = run(
        ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"],
        cwd=workspace,
        check=False,
        timeout=timeout,
    )
    if expect_success and result.returncode != 0:
        raise AssertionError(f"terraform destroy failed:\n{result.stdout}\n{result.stderr}")
    if not expect_success and result.returncode == 0:
        raise AssertionError("terraform destroy unexpectedly succeeded")
    return result


def tf_plan(workspace, *, refresh=True, timeout=90):
    command = ["terraform", "plan", "-input=false", "-no-color", "-detailed-exitcode"]
    if not refresh:
        command.append("-refresh=false")
    return run(command, cwd=workspace, check=False, timeout=timeout)


def tf_plan_json(workspace, *, refresh=True, timeout=90):
    plan_path = pathlib.Path(workspace) / "plan.bin"
    command = [
        "terraform",
        "plan",
        "-input=false",
        "-no-color",
        "-detailed-exitcode",
        "-out",
        str(plan_path),
    ]
    if not refresh:
        command.append("-refresh=false")
    result = run(command, cwd=workspace, check=False, timeout=timeout)
    if result.returncode not in (0, 2):
        raise AssertionError(f"terraform plan failed:\n{result.stdout}\n{result.stderr}")
    shown = run(["terraform", "show", "-json", str(plan_path)], cwd=workspace)
    return result, json.loads(shown.stdout)


def plan_actions(plan, address):
    for change in plan.get("resource_changes", []):
        if change.get("address") == address:
            return change.get("change", {}).get("actions", [])
    return []


def tf_show(workspace):
    result = run(["terraform", "show", "-json"], cwd=workspace)
    return json.loads(result.stdout)


def tf_state_pull(workspace):
    result = run(["terraform", "state", "pull"], cwd=workspace)
    return json.loads(result.stdout)


def resources_from_show(show):
    found = []

    def visit(module):
        found.extend(module.get("resources", []))
        for child in module.get("child_modules", []):
            visit(child)

    root = show.get("values", {}).get("root_module")
    if root:
        visit(root)
    return found


def resource_values(workspace, address):
    for resource in resources_from_show(tf_show(workspace)):
        if resource.get("address") == address:
            return resource.get("values", {})
    raise AssertionError(f"resource {address} not found in terraform show")


def state_has_resource(workspace, address):
    return any(resource.get("address") == address for resource in resources_from_show(tf_show(workspace)))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_ansible_wrapper(tmp_path, *, counter=None, fail_flag=None, sleep_flag=None):
    wrapper = tmp_path / "ansible-wrapper"
    lines = ["#!/bin/sh", "set -eu"]
    if counter is not None:
        lines.append(f"printf 'x\\n' >> {hcl_string(counter)}")
    if fail_flag is not None:
        lines.extend([f"if [ -e {hcl_string(fail_flag)} ]; then", "  exit 42", "fi"])
    if sleep_flag is not None:
        lines.extend([f"if [ -e {hcl_string(sleep_flag)} ]; then", "  sleep 30", "fi"])
    lines.append(f"exec {hcl_string(REAL_ANSIBLE)} \"$@\"")
    wrapper.write_text("\n".join(lines) + "\n", encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def counter_value(path):
    path = pathlib.Path(path)
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def unique_unix_name(prefix="aops"):
    return (prefix + uuid.uuid4().hex[:8])[:24]


def remove_path(path):
    path = pathlib.Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def remove_user(name, remove_home=True):
    command = ["userdel"]
    if remove_home:
        command.append("-r")
    command.append(name)
    run(command, check=False)


def remove_group(name):
    run(["groupdel", name], check=False)


def remove_crontab(user="root"):
    run(["crontab", "-u", user, "-r"], check=False)


@pytest.fixture
def cleanup_registry():
    callbacks = []

    class Registry:
        def path(self, value):
            callbacks.append(lambda: remove_path(value))
            return value

        def user(self, name, remove_home=True):
            callbacks.append(lambda: remove_user(name, remove_home=remove_home))
            return name

        def group(self, name):
            callbacks.append(lambda: remove_group(name))
            return name

        def cron(self, user="root"):
            callbacks.append(lambda: remove_crontab(user))
            return user

        def callback(self, fn):
            callbacks.append(fn)
            return fn

    registry = Registry()
    try:
        yield registry
    finally:
        for callback in reversed(callbacks):
            try:
                callback()
            except Exception:
                pass
