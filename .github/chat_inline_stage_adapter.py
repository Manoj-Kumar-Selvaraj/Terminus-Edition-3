#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
WORK = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "chat-inline"
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.control_plane import resolve_control_plane_commit
from execution.invocation import StageInvocationBuilder
from retrieval.models import InvocationContext


def run(*args: str, capture: bool = False) -> str:
    cp = subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=capture)
    return cp.stdout.strip() if capture else ""


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def remote_main() -> str:
    return run("git", "ls-remote", "origin", "refs/heads/main", capture=True).split()[0]


def task_tree(commit: str, task: str) -> str:
    return run("git", "rev-parse", f"{commit}:{task}", capture=True)


def assert_control(head: str, expected: str) -> None:
    actual = resolve_control_plane_commit(ROOT, head=head)
    if actual != expected:
        raise SystemExit(f"control-plane changed expected={expected} actual={actual}")


sha = os.environ["GITHUB_SHA"]
changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha, "--", ".terminus/chat-exec/*.json", capture=True).splitlines()
if len(changed) != 1:
    raise SystemExit(f"expected exactly one reconciliation request, found {changed}")
req = load(ROOT / changed[0])
required = {
    "schema_version", "mode", "task_id", "input_task_commit", "output_task_commit",
    "control_plane_commit", "expected_repository_head", "discovery_run_id",
    "previous_a5_invocation", "expected_changed_files",
}
if set(req) != required or req["schema_version"] != "1.0" or req["mode"] != "RECONCILE_A5_LINT":
    raise SystemExit("invalid A5 reconciliation request")

task = req["task_id"]
input_task = req["input_task_commit"]
output_task = req["output_task_commit"]
control = req["control_plane_commit"]
expected_head = req["expected_repository_head"]
discovery_run = req["discovery_run_id"]
prior_inv = req["previous_a5_invocation"]
expected_files = sorted(req["expected_changed_files"])

run("git", "fetch", "origin", "main")
run("git", "cat-file", "-e", f"{input_task}^{{commit}}")
run("git", "cat-file", "-e", f"{output_task}^{{commit}}")
if subprocess.run(["git", "merge-base", "--is-ancestor", input_task, output_task], cwd=ROOT).returncode != 0:
    raise SystemExit("lint-fix output task is not a descendant of A5 input task")
actual_files = sorted(run("git", "diff", "--name-only", input_task, output_task, "--", task, capture=True).splitlines())
if actual_files != expected_files:
    raise SystemExit(f"unexpected lint-fix task delta expected={expected_files} actual={actual_files}")
numstat = run("git", "diff", "--numstat", input_task, output_task, "--", *expected_files, capture=True).splitlines()
if len(numstat) != 2 or any(not line.startswith("0\t1\t") for line in numstat):
    raise SystemExit(f"lint-fix delta is not exactly two one-line deletions: {numstat}")

base = remote_main()
if base != expected_head:
    changed_scope = subprocess.run([
        "git", "diff", "--quiet", expected_head, base, "--",
        task, f".terminus/executions/{task}", f".terminus/designs/{task}.json",
        f".terminus/designs/{task}-test-map.json",
    ], cwd=ROOT).returncode != 0
    if changed_scope:
        raise SystemExit(f"main moved in EC2 scope expected={expected_head} current={base}")
assert_control(base, control)
if task_tree(base, task) != task_tree(output_task, task):
    raise SystemExit("current main task tree does not equal the dedicated lint-fix snapshot")

# Detach from the transport branch before any canonical mutation.
run("git", "checkout", "--detach", base)
assert_control(base, control)

prior_path = ROOT / ".terminus" / "executions" / task / f"{prior_inv}.result.json"
prior = load(prior_path)
inputs = dict(prior["invocation_snapshot"]["inputs"]["required"])
context = InvocationContext(
    stage_id="VERIFIER_BUILD",
    role_id="A5_VERIFIER_AUTHOR",
    task_id=task,
    task_commit=input_task,
    control_plane_commit=control,
    ci_run_id=str(discovery_run),
)
invocation = StageInvocationBuilder(ROOT).build(context, inputs)
if invocation.get("readiness") != "READY":
    raise SystemExit(f"A5 reconciliation invocation not READY: {invocation.get('missing_required_inputs')}")
if invocation["stage"]["stage_id"] != "VERIFIER_BUILD" or invocation["stage"]["role_class"] != "PRODUCER":
    raise SystemExit("A5 reconciliation invocation has wrong stage authority")
if invocation["invocation_id"] == prior_inv:
    raise SystemExit("A5 reconciliation did not obtain a fresh invocation identity")
dump(WORK / "invocation.json", invocation)

# Execute the registered A5 deterministic validators on the repaired task tree.
run("python3", "-m", "pip", "install", "--disable-pip-version-check", "ruff==0.12.8")
run("ruff", "check", f"{task}/tests")
run("python3", ".terminus/validate_task_complexity.py", task)

outputs = dict(prior["outputs"])
result = {
    "schema_version": "1.0",
    "invocation_id": invocation["invocation_id"],
    "status": "VERIFIER_READY",
    "outputs": outputs,
    "output_task_commit": output_task,
    "evidence_refs": [],
}
dump(WORK / "result.json", result)
run("python3", ".terminus/execution/controller_cli.py", "record", "--invocation", str(WORK / "invocation.json"), "--result", str(WORK / "result.json"), "--output", str(WORK / "record.json"))

porcelain = run("git", "status", "--porcelain", capture=True).splitlines()
paths = [line[3:] for line in porcelain]
unexpected = [path for path in paths if not path.startswith(f".terminus/executions/{task}/")]
if unexpected:
    raise SystemExit(f"unexpected reconciliation mutations: {unexpected}")
run("git", "config", "user.name", "terminus-chat-adapter[bot]")
run("git", "config", "user.email", "terminus-chat-adapter[bot]@users.noreply.github.com")
run("git", "add", "--", f".terminus/executions/{task}")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise SystemExit("A5 reconciliation produced no canonical execution mutation")
run("git", "commit", "-m", f"Reconcile {task} VERIFIER_BUILD lint fix")

latest = remote_main()
if latest != base:
    run("git", "fetch", "origin", "main")
    if subprocess.run(["git", "diff", "--quiet", base, latest, "--", task, f".terminus/executions/{task}"], cwd=ROOT).returncode != 0:
        raise SystemExit(f"main moved in EC2 scope during A5 record base={base} current={latest}")
    assert_control(latest, control)
    if task_tree(latest, task) != task_tree(output_task, task):
        raise SystemExit("latest main task tree changed during A5 reconciliation")
    run("git", "rebase", "origin/main")
    base = latest
run("git", "push", "origin", "HEAD:main")

# Prove the reconciled controller now continues from the lint-fix task snapshot.
empty = WORK / "empty-inputs.json"
dump(empty, {})
run("python3", ".terminus/execution/controller_cli.py", "continue", "--task-id", task, "--task-commit", output_task, "--control-plane-commit", control, "--inputs-json", str(empty), "--output", str(WORK / "continue-after.json"))
after = load(WORK / "continue-after.json")
next_stage = after.get("next", {}).get("stage_id")
if next_stage != "HUMAN_WRITING_RESEARCH":
    raise SystemExit(f"A5 reconciliation did not advance to A6: {after.get('next')}")
