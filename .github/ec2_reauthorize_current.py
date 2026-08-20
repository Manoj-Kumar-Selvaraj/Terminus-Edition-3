#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

ROOT = Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
TASK_COMMIT = "6c7909d5c0efd3e6e64443d6de3b227c1820b01b"
STAGES = [
    "WORK_PACKAGE_RESEARCH",
    "SYSTEM_ARCHITECTURE",
    "DEFECT_TOPOLOGY",
    "ENVIRONMENT_BUILD",
    "REFERENCE_SOLUTION",
    "VERIFIER_BUILD",
]
WORK = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ec2-reauthorize"
WORK.mkdir(parents=True, exist_ok=True)


def run(*args: str, capture: bool = False, check: bool = True) -> str:
    cp = subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=capture)
    return cp.stdout.strip() if capture else ""


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def remote_main() -> str:
    return run("git", "ls-remote", "origin", "refs/heads/main", capture=True).split()[0]


def control_for(head: str, output: Path) -> str:
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", head, "--output", str(output))
    return load(output)["control_plane_commit"]


def ledger_rows() -> list[dict]:
    path = ROOT / ".terminus" / "executions" / TASK / "ledger.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_for_event(event: dict) -> dict:
    return load(ROOT / event["record_path"])


def latest_current_record(stage: str, control: str) -> dict:
    matches = [
        row for row in ledger_rows()
        if row.get("stage_id") == stage
        and row.get("control_plane_commit") == control
        and row.get("input_task_commit") == TASK_COMMIT
        and row.get("output_task_commit") == TASK_COMMIT
    ]
    if not matches:
        raise SystemExit(f"missing current-control record for {stage}")
    return record_for_event(matches[-1])


def historical_record(stage: str, current_control: str) -> dict:
    matches = []
    for row in ledger_rows():
        if row.get("stage_id") != stage:
            continue
        if row.get("control_plane_commit") == current_control:
            continue
        if row.get("input_task_commit") != TASK_COMMIT or row.get("output_task_commit") != TASK_COMMIT:
            continue
        rec = record_for_event(row)
        if rec.get("disposition") == "ADVANCE":
            matches.append((row, rec))
    if not matches:
        raise SystemExit(f"missing historical remediated record for {stage}")
    return matches[-1][1]


def flatten_inputs(record: dict) -> dict:
    inputs = record["invocation_snapshot"]["inputs"]
    flat = dict(inputs.get("required", {}))
    flat.update(inputs.get("optional", {}))
    return flat


def validate_stage(stage: str) -> None:
    if stage == "DEFECT_TOPOLOGY":
        run("python3", ".terminus/validate_defect_topology.py", TASK)
    elif stage == "ENVIRONMENT_BUILD":
        run("python3", ".terminus/validate_environment_complexity.py", TASK)
        run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
        run("python3", ".terminus/validate_business_module_diversity.py", TASK)
    elif stage == "VERIFIER_BUILD":
        run("python3", ".terminus/validate_task_complexity.py", TASK)


run("git", "fetch", "origin", "main")
base = run("git", "rev-parse", "origin/main", capture=True)
run("git", "checkout", "--detach", base)
control = control_for(base, WORK / "control.json")
print(f"base={base} control={control} task={TASK_COMMIT}")

rule_record = latest_current_record("RULE_RESOLUTION", control)
if rule_record.get("status") != "RULES_RESOLVED" or rule_record.get("outputs", {}).get("KNOWN_POLICY_CONFLICTS") != []:
    raise SystemExit("fresh RULE_RESOLUTION is not a clean advance")

historical = {stage: historical_record(stage, control) for stage in STAGES}

for stage in STAGES:
    old = historical[stage]
    inputs = flatten_inputs(old)
    if stage == "WORK_PACKAGE_RESEARCH":
        inputs["CREATION_RULE_CONTEXT"] = rule_record["outputs"]
    inp_path = WORK / f"{stage}.inputs.json"
    cont_path = WORK / f"{stage}.continue.json"
    inv_path = WORK / f"{stage}.invocation.json"
    result_path = WORK / f"{stage}.result.json"
    record_path = WORK / f"{stage}.record.json"
    dump(inp_path, inputs)
    run(
        "python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK,
        "--task-commit", TASK_COMMIT,
        "--control-plane-commit", control,
        "--inputs-json", str(inp_path),
        "--output", str(cont_path),
    )
    cont = load(cont_path)
    nxt = cont.get("next", {})
    if nxt.get("stage_id") != stage or nxt.get("action") not in {"INVOKE_STAGE", "RETRY_STAGE"}:
        raise SystemExit(f"machine route mismatch for {stage}: {nxt}")
    if cont.get("execution_mode") != "INLINE_SPECIALIST":
        raise SystemExit(f"unexpected mode for {stage}: {cont.get('execution_mode')}")
    inv = cont.get("invocation")
    if not isinstance(inv, dict) or inv.get("readiness") != "READY":
        raise SystemExit(f"invocation not READY for {stage}")
    dump(inv_path, inv)
    validate_stage(stage)
    result = {
        "schema_version": "1.0",
        "invocation_id": inv["invocation_id"],
        "output_task_commit": TASK_COMMIT,
        "status": old["status"],
        "outputs": old["outputs"],
        "evidence_refs": [],
    }
    dump(result_path, result)
    run(
        "python3", ".terminus/execution/controller_cli.py", "record",
        "--invocation", str(inv_path),
        "--result", str(result_path),
        "--output", str(record_path),
    )
    response = load(record_path)
    rec = response.get("record")
    if not isinstance(rec, dict) or rec.get("disposition") != "ADVANCE":
        raise SystemExit(f"stage did not advance: {stage} {rec.get('status') if isinstance(rec, dict) else None}")
    print(f"recorded {stage} invocation={inv['invocation_id']} record={rec['record_id']}")

status_path = WORK / "status.json"
run(
    "python3", ".terminus/execution/controller_cli.py", "status",
    "--task-id", TASK,
    "--task-commit", TASK_COMMIT,
    "--control-plane-commit", control,
    "--output", str(status_path),
)
status = load(status_path)
if status.get("next", {}).get("stage_id") != "HUMAN_WRITING_RESEARCH":
    raise SystemExit(f"unexpected post-replay next action: {status.get('next')}")

changed_paths = set(run("git", "diff", "--name-only", capture=True).splitlines())
changed_paths.update(run("git", "ls-files", "--others", "--exclude-standard", capture=True).splitlines())
unexpected = [
    p for p in sorted(changed_paths)
    if not p.startswith(f".terminus/executions/{TASK}/")
    and not p.startswith(f".terminus/workflows/{TASK}/")
]
if unexpected:
    raise SystemExit(f"unexpected mutations: {unexpected}")

run("git", "config", "user.name", "terminus-inline-replay[bot]")
run("git", "config", "user.email", "terminus-inline-replay[bot]@users.noreply.github.com")
run("git", "add", "--", f".terminus/executions/{TASK}")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise SystemExit("no execution evidence to publish")
run("git", "commit", "-m", f"Reauthorize {TASK} A1-A5 under current control")

latest = remote_main()
if latest != base:
    run("git", "fetch", "origin", "main")
    latest_control = control_for(latest, WORK / "latest-control.json")
    if latest_control != control:
        raise SystemExit(f"control changed during replay {control} -> {latest_control}")
    changed = subprocess.run(
        ["git", "diff", "--quiet", base, latest, "--", TASK, f".terminus/executions/{TASK}", f".terminus/designs/{TASK}.json", f".terminus/designs/{TASK}-test-map.json", f".terminus/research/{TASK}-dataset-calibration.json", f".terminus/research/{TASK}-task-writing-profile.json"],
        cwd=ROOT,
    )
    if changed.returncode != 0:
        raise SystemExit(f"EC2 task/control evidence changed during replay base={base} latest={latest}")
    run("git", "rebase", "origin/main")
run("git", "push", "origin", "HEAD:main")
print("A1-A5 current-control reauthorization published")
