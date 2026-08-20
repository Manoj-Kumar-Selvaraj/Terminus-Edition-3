#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

ROOT = Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
TASK_COMMIT = "6c7909d5c0efd3e6e64443d6de3b227c1820b01b"
STAGE = "HUMAN_WRITING_RESEARCH"
WORK = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ec2-hwr-current"
WORK.mkdir(parents=True, exist_ok=True)


def run(*args: str, capture: bool = False, check: bool = True) -> str:
    cp = subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=capture)
    return cp.stdout.strip() if capture else ""


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def ledger_rows() -> list[dict]:
    p = ROOT / ".terminus" / "executions" / TASK / "ledger.jsonl"
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def rec(row: dict) -> dict:
    return load(ROOT / row["record_path"])


def latest_current(stage: str, control: str) -> dict:
    rows = [r for r in ledger_rows() if r.get("stage_id") == stage and r.get("control_plane_commit") == control and r.get("input_task_commit") == TASK_COMMIT and r.get("output_task_commit") == TASK_COMMIT]
    if not rows:
        raise SystemExit(f"missing current record {stage}")
    return rec(rows[-1])


def latest_historical(stage: str, control: str) -> dict:
    found = []
    for row in ledger_rows():
        if row.get("stage_id") != stage or row.get("control_plane_commit") == control:
            continue
        r = rec(row)
        if r.get("disposition") == "ADVANCE":
            found.append(r)
    if not found:
        raise SystemExit(f"missing historical record {stage}")
    return found[-1]


def remote_main() -> str:
    return run("git", "ls-remote", "origin", "refs/heads/main", capture=True).split()[0]


def control_for(head: str, out: Path) -> str:
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", head, "--output", str(out))
    return load(out)["control_plane_commit"]


run("git", "fetch", "origin", "main")
base = run("git", "rev-parse", "origin/main", capture=True)
run("git", "checkout", "--detach", base)
control = control_for(base, WORK / "control.json")

status_path = WORK / "status.json"
run("python3", ".terminus/execution/controller_cli.py", "status", "--task-id", TASK, "--task-commit", TASK_COMMIT, "--control-plane-commit", control, "--output", str(status_path))
status = load(status_path)
if status.get("next", {}).get("stage_id") != STAGE:
    raise SystemExit(f"machine next is not HWR: {status.get('next')}")

old = latest_historical(STAGE, control)
old_inputs = old["invocation_snapshot"]["inputs"]
inputs = dict(old_inputs.get("required", {}))
inputs.update(old_inputs.get("optional", {}))

a1 = latest_current("WORK_PACKAGE_RESEARCH", control)
recommendation = a1["outputs"]["RECOMMENDATION"]
candidates = a1["outputs"]["CANDIDATES"]
selected = next(c for c in candidates if c.get("ID") == recommendation)
old_wp = inputs["APPROVED_WORK_PACKAGE"]
inputs["APPROVED_WORK_PACKAGE"] = {key: selected[key] for key in old_wp}

solver = dict(inputs["SOLVER_VISIBLE_REQUIREMENTS"])
for rel in list(solver):
    if rel == "instruction.md":
        path = ROOT / TASK / "instruction.md"
    else:
        path = ROOT / TASK / "environment" / "enforcer" / rel
    solver[rel] = path.read_text(encoding="utf-8")
inputs["SOLVER_VISIBLE_REQUIREMENTS"] = solver

dump(WORK / "inputs.json", inputs)
run("python3", ".terminus/execution/controller_cli.py", "continue", "--task-id", TASK, "--task-commit", TASK_COMMIT, "--control-plane-commit", control, "--inputs-json", str(WORK / "inputs.json"), "--output", str(WORK / "continue.json"))
cont = load(WORK / "continue.json")
if cont.get("next", {}).get("stage_id") != STAGE or cont.get("execution_mode") != "INLINE_SPECIALIST":
    raise SystemExit(f"unexpected HWR route: {cont.get('next')} mode={cont.get('execution_mode')}")
inv = cont.get("invocation")
if not isinstance(inv, dict) or inv.get("readiness") != "READY":
    raise SystemExit("HWR invocation not READY")
dump(WORK / "invocation.json", inv)

pair_path = f".terminus/research/{TASK}-dataset-calibration.json"
profile_path = f".terminus/research/{TASK}-task-writing-profile.json"
run("python3", ".terminus/human_writing/validate_calibration.py", "--root", ".", "--pair", pair_path, "--profile", profile_path)

outputs = dict(old["outputs"])
outputs["CURRENT_STATE_EVIDENCE_NOTES"] = [
    "Existing EC2 security-domain calibration pair and task-writing profile were revalidated against the current repository dataset policy and current solver-visible task contract.",
    "No Oracle, verifier-private, prior-review, model-trial, or private defect evidence was consumed by this Human Writing Research execution.",
]
result = {"schema_version":"1.0","invocation_id":inv["invocation_id"],"output_task_commit":TASK_COMMIT,"status":"CALIBRATION_READY","outputs":outputs,"evidence_refs":[]}
dump(WORK / "result.json", result)
run("python3", ".terminus/execution/controller_cli.py", "record", "--invocation", str(WORK / "invocation.json"), "--result", str(WORK / "result.json"), "--output", str(WORK / "record.json"))
response = load(WORK / "record.json")
record = response.get("record")
if not isinstance(record, dict) or record.get("disposition") != "ADVANCE" or record.get("transition", {}).get("target") != "INSTRUCTION_DRAFT":
    raise SystemExit(f"HWR did not advance: {record}")

changed = set(run("git", "diff", "--name-only", capture=True).splitlines())
changed.update(run("git", "ls-files", "--others", "--exclude-standard", capture=True).splitlines())
unexpected = [p for p in sorted(changed) if not p.startswith(f".terminus/executions/{TASK}/") and not p.startswith(f".terminus/workflows/{TASK}/")]
if unexpected:
    raise SystemExit(f"unexpected HWR mutations: {unexpected}")

run("git", "config", "user.name", "terminus-ec2-hwr[bot]")
run("git", "config", "user.email", "terminus-ec2-hwr[bot]@users.noreply.github.com")
run("git", "add", "--", f".terminus/executions/{TASK}")
run("git", "commit", "-m", f"Record {TASK} {STAGE} under current control")
latest = remote_main()
if latest != base:
    run("git", "fetch", "origin", "main")
    if control_for(latest, WORK / "latest-control.json") != control:
        raise SystemExit("control changed during HWR")
    diff = subprocess.run(["git","diff","--quiet",base,latest,"--",TASK,f".terminus/executions/{TASK}",pair_path,profile_path],cwd=ROOT)
    if diff.returncode != 0:
        raise SystemExit("EC2 scope changed during HWR")
    run("git", "rebase", "origin/main")
run("git", "push", "origin", "HEAD:main")
print(f"HWR current-control PASS invocation={inv['invocation_id']} record={record['record_id']}")
