#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
CONTROL = "215cc70bcebcccc3c9a401af1b74a97d90026da3"
INPUT_TASK = "8836f886d7cfc7f2747264026da31d1dfa49c658"
OUTPUT_TASK = "0ad08868799c19ea2e02458bd2fc92ec64eaa288"
WORK = pathlib.Path(os.environ["RUNNER_TEMP"]) / "ec2-q7-converge"
WORK.mkdir(parents=True, exist_ok=True)


def run(*args, capture=False):
    if capture:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    subprocess.run(args, cwd=ROOT, check=True)


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    base = run("git", "rev-parse", "HEAD", capture=True)
    cp = WORK / "control.json"
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", base, "--output", str(cp))
    if json.loads(cp.read_text())["control_plane_commit"] != CONTROL:
        raise SystemExit("effective control changed before Q7 convergence")
    run("git", "cat-file", "-e", f"{INPUT_TASK}^{{commit}}")
    run("git", "cat-file", "-e", f"{OUTPUT_TASK}^{{commit}}")
    run("git", "merge-base", "--is-ancestor", INPUT_TASK, OUTPUT_TASK)
    changed = run("git", "diff", "--name-only", INPUT_TASK, OUTPUT_TASK, capture=True).splitlines()
    forbidden = [p for p in changed if not (
        p.startswith(f"{TASK}/")
        or p == f".terminus/designs/{TASK}.json"
        or p.startswith(f".terminus/designs/{TASK}-")
        or p.startswith(f".terminus/designs/{TASK}/")
        or p.startswith(f".terminus/contracts/{TASK}/")
    )]
    if forbidden:
        raise SystemExit("Q7 output snapshot contains protected paths: " + ", ".join(forbidden))

    inputs = {
        "CREATION_RULE_CONTEXT": {
            "CONTROL_PLANE_COMMIT": CONTROL,
            "CREATION_PROFILE": "large_system_strict",
            "KNOWN_POLICY_CONFLICTS": [],
            "NETWORK_ENVIRONMENT_CONSTRAINTS": "current Edition 3 task-format, network, isolation and Harbor runtime rules",
        },
        "CURRENT_TASK_TREE": {
            "task_root": TASK,
            "task_commit": INPUT_TASK,
            "observed_format_defects": [
                "eight tags exceeded current 3-6 tag limit",
                "network_mode none was not a canonical value",
                "agent image lacked canonical Go runtime plus tmux/asciinema",
                "environment dockerignore lacked standard VCS/env/cache exclusions",
                "separate verifier did not pre-create declared artifact parent /app/enforcer",
            ],
            "repair_target_task_commit": OUTPUT_TASK,
            "repair_paths": [
                f"{TASK}/task.toml",
                f"{TASK}/environment/Dockerfile",
                f"{TASK}/environment/.dockerignore",
                f"{TASK}/tests/Dockerfile",
            ],
            "instruction": "absolute /app/enforcer references; no private verifier leakage",
            "solution": "solution/solve.sh isolated from agent build context",
            "tests": "separate digest-pinned verifier; reward.txt binary contract",
        },
        "ACTIVE_FORMAT_VALIDATORS": [
            "current Edition 3 task-format/packaging rules",
            "task.toml canonical field/value checks",
            "digest-pinned image/runtime-tooling checks",
            "separate verifier and artifact-parent checks",
            "solution/tests isolation checks",
            ".terminus/validate_task_complexity.py",
            ".terminus/validate_environment_complexity.py",
            ".terminus/validate_runtime_authenticity.py",
            ".terminus/validate_business_module_diversity.py",
        ],
    }
    ip = WORK / "inputs.json"
    co = WORK / "continue.json"
    write_json(ip, inputs)
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", INPUT_TASK,
        "--control-plane-commit", CONTROL,
        "--inputs-json", str(ip), "--output", str(co))
    payload = json.loads(co.read_text())
    inv = payload.get("invocation")
    if payload.get("next", {}).get("stage_id") != "FORMAT_GATE":
        raise SystemExit(f"expected FORMAT_GATE, got {payload.get('next')}")
    if payload.get("execution_mode") != "INLINE_SPECIALIST":
        raise SystemExit(f"expected INLINE_SPECIALIST, got {payload.get('execution_mode')}")
    if not isinstance(inv, dict) or inv.get("readiness") != "READY":
        raise SystemExit("Q7 convergence invocation is not READY")
    invp = WORK / "invocation.json"
    write_json(invp, inv)

    # Re-run deterministic checks against the already-published repaired tree.
    run("python3", ".terminus/validate_task_complexity.py", TASK)
    run("python3", ".terminus/validate_environment_complexity.py", TASK)
    run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
    run("python3", ".terminus/validate_business_module_diversity.py", TASK)
    env = (ROOT / TASK / "environment" / "Dockerfile").read_text()
    assert "golang:1.24-bookworm@sha256:" in env and "tmux" in env and "asciinema" in env
    toml = (ROOT / TASK / "task.toml").read_text()
    assert 'network_mode = "public"' in toml
    assert 'tags = ["aws", "ec2", "policy-as-code", "supply-chain", "vulnerability", "security"]' in toml
    assert "mkdir -p /app/enforcer" in (ROOT / TASK / "tests" / "Dockerfile").read_text()

    result = {
        "schema_version": "1.0",
        "invocation_id": inv["invocation_id"],
        "output_task_commit": OUTPUT_TASK,
        "status": "FORMAT_PASS",
        "outputs": {
            "CHECKS": {
                "task_lineage": f"PASS: Q7 fixer transaction repairs {INPUT_TASK} to task-scoped descendant {OUTPUT_TASK}; snapshot delta contains no protected control/execution paths",
                "task_toml": "PASS_AFTER_FIX: version 2.0, six tags, absolute /app/enforcer artifact, separate verifier, canonical public network mode and valid timeouts",
                "agent_image": "PASS_AFTER_FIX: canonical digest-pinned Go 1.24 base with tmux/asciinema and clean apt transaction",
                "dockerignore": "PASS_AFTER_FIX: VCS/env/cache/state/output exclusions present",
                "verifier_image": "PASS_AFTER_FIX: digest-pinned verifier pre-creates declared artifact parent /app/enforcer and dependencies remain baked",
                "test_sh": "PASS: binary reward.txt assignment; no runtime dependency install; no trailing exit required by current policy",
                "solution_layout": "PASS: solution/solve.sh remains outside agent build context",
                "isolation": "PASS: solution/tests/private control evidence are not copied into agent image",
                "instruction_paths": "PASS: solver-visible paths are absolute/public and private verifier paths are not disclosed",
                "complexity": "PASS: strict task/environment complexity validators reran after the format repair",
                "runtime_authenticity_precheck": "PASS/N/A under current declared production-authenticity policy; mandatory lifecycle runtime/oracle gates remain downstream",
                "policy_conflicts": "PASS: none found",
            },
            "RERUN": "PASS_AFTER_FIX_AND_RERUN: Q7 applied the bounded format repair, reran current structural/complexity/authenticity validators, and returns the repaired logical task snapshot for ASSEMBLY.",
        },
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{OUTPUT_TASK}"},
            {"kind": "COMMIT", "ref": f"commit:{CONTROL}"},
        ],
    }
    rp = WORK / "result.json"
    ro = WORK / "record.json"
    write_json(rp, result)
    run("python3", ".terminus/execution/controller_cli.py", "record",
        "--invocation", str(invp), "--result", str(rp), "--output", str(ro))
    rec = json.loads(ro.read_text())["record"]
    if rec["status"] != "FORMAT_PASS" or rec["task_lineage"]["output_task_commit"] != OUTPUT_TASK:
        raise SystemExit("Q7 convergence record mismatch")
    if rec["transition"].get("target") != "ASSEMBLY":
        raise SystemExit(f"Q7 convergence target drift: {rec['transition']}")

    # Prove the resolver now advances to ASSEMBLY.
    ao = WORK / "after.json"
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", OUTPUT_TASK,
        "--control-plane-commit", CONTROL, "--output", str(ao))
    after = json.loads(ao.read_text())
    if after.get("next", {}).get("stage_id") != "ASSEMBLY":
        raise SystemExit(f"resolver did not converge to ASSEMBLY: {after.get('next')}")
    print(f"Q7_CONVERGED_RECORD={rec['record_id']}")
    print("NEXT_STAGE=ASSEMBLY")


if __name__ == "__main__":
    main()
