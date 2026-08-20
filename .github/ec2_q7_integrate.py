#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
CONTROL = "215cc70bcebcccc3c9a401af1b74a97d90026da3"
INPUT_TASK = "8836f886d7cfc7f2747264026da31d1dfa49c658"
SNAPSHOT = "0ad08868799c19ea2e02458bd2fc92ec64eaa288"
SNAPSHOT_BRANCH = "task/ec2-artifact-policy-enforcement-q7-snapshot-20260820"
EXPECTED_FIXED_INV = "inv_86855ffa6d86ce327510ad6b7cfd4550239627a3f7d0e236ae8a80b36f048300"
EXPECTED_PASS_INV = "inv_7bc71b3b73f2d9851595532a9953f86f963b1b590ac78517241fa9771d3cda21"
EXPECTED_FIXED_RECORD = "rec_450d6759664d6ba5f33df7b64c6b4de5f584e148911107f0d4850868bc5d2404"
EXPECTED_PASS_RECORD = "rec_4400f43bdc0bf87febb00c942cdef33c1b80d32299c81220820360d921f60409"
WORK = pathlib.Path(os.environ["RUNNER_TEMP"]) / "ec2-q7-integrate"
WORK.mkdir(parents=True, exist_ok=True)
FIX_PATHS = [
    f"{TASK}/task.toml",
    f"{TASK}/environment/Dockerfile",
    f"{TASK}/environment/.dockerignore",
    f"{TASK}/tests/Dockerfile",
]


def run(*args, capture=False):
    if capture:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    subprocess.run(args, cwd=ROOT, check=True)


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def inputs(fixed):
    return {
        "CREATION_RULE_CONTEXT": {
            "CONTROL_PLANE_COMMIT": CONTROL,
            "CREATION_PROFILE": "large_system_strict",
            "KNOWN_POLICY_CONFLICTS": [],
            "NETWORK_ENVIRONMENT_CONSTRAINTS": "current Edition 3 task-format, network, isolation and Harbor runtime rules",
        },
        "CURRENT_TASK_TREE": {
            "task_root": TASK,
            "top_level": [".gitattributes", "README.md", "environment/", "instruction.md", "solution/", "task.toml", "tests/"],
            "task_toml": {
                "version": "2.0", "name": TASK, "artifacts": ["/app/enforcer"],
                "verifier_environment_mode": "separate",
                "network_mode": "public" if fixed else "none",
                "agent_timeout_sec": 10800, "verifier_timeout_sec": 1800,
                "tag_count": 6 if fixed else 8, "workdir": "/app/enforcer",
            },
            "environment": {
                "Dockerfile": "digest-pinned canonical Go base with ca-certificates/tmux/asciinema" if fixed else "digest-pinned Python base with apt Go; missing tmux/asciinema",
                "dockerignore": "standard context exclusions plus state/out/tmp" if fixed else "state/out/tmp only",
                "source_dir": "environment/enforcer/",
            },
            "tests": {
                "Dockerfile": "digest-pinned separate verifier with pytest pins, Go, and /app/enforcer artifact parent" if fixed else "digest-pinned separate verifier with pytest pins and Go; missing /app/enforcer artifact parent",
                "test_sh": "runtime reward.txt 0/1 contract; dependencies baked; no trailing exit required by current checklist",
                "private_test_files": ["test_outputs.py", "verifier_lib.py"],
            },
            "instruction": "instruction.md uses absolute /app/enforcer paths and solver-visible public contract paths",
            "solution": {"entrypoint": "solution/solve.sh"},
        },
        "ACTIVE_FORMAT_VALIDATORS": [
            "current Edition 3 task-format/packaging rules",
            "task.toml canonical field/value checks",
            "digest-pinned image/runtime-tooling checks",
            "separate verifier and artifact-parent checks",
            "solution/tests isolation checks",
            "Q7 Task Format Enforcer same-chat review",
        ],
    }


def compile_inv(task_commit, fixed, label, expected_inv):
    inp = WORK / f"{label}-inputs.json"
    out = WORK / f"{label}-continue.json"
    write_json(inp, inputs(fixed))
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", task_commit,
        "--control-plane-commit", CONTROL,
        "--inputs-json", str(inp), "--output", str(out))
    payload = json.loads(out.read_text())
    inv = payload.get("invocation")
    assert payload.get("next", {}).get("stage_id") == "FORMAT_GATE", payload.get("next")
    assert payload.get("execution_mode") == "INLINE_SPECIALIST", payload.get("execution_mode")
    assert isinstance(inv, dict) and inv.get("readiness") == "READY"
    if inv["invocation_id"] != expected_inv:
        raise SystemExit(f"invocation drift expected={expected_inv} actual={inv['invocation_id']}")
    p = WORK / f"{label}-invocation.json"
    write_json(p, inv)
    return inv, p


def record(inv, inv_path, status, outputs, expected_id, label):
    rp = WORK / f"{label}-result.json"
    op = WORK / f"{label}-record.json"
    write_json(rp, {
        "schema_version": "1.0",
        "invocation_id": inv["invocation_id"],
        "output_task_commit": SNAPSHOT,
        "status": status,
        "outputs": outputs,
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{SNAPSHOT}"},
            {"kind": "COMMIT", "ref": f"commit:{CONTROL}"},
        ],
    })
    run("python3", ".terminus/execution/controller_cli.py", "record",
        "--invocation", str(inv_path), "--result", str(rp), "--output", str(op))
    rec = json.loads(op.read_text())["record"]
    if rec["record_id"] != expected_id:
        raise SystemExit(f"{status} replay record drift expected={expected_id} actual={rec['record_id']}")
    print(f"REPLAYED {status} record={rec['record_id']}")
    return rec


def main():
    base = run("git", "rev-parse", "HEAD", capture=True)
    run("git", "cat-file", "-e", f"{SNAPSHOT}^{{commit}}")
    control_path = WORK / "control.json"
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", base, "--output", str(control_path))
    if json.loads(control_path.read_text())["control_plane_commit"] != CONTROL:
        raise SystemExit("effective control changed before Q7 integration")

    changed = run("git", "diff", "--name-only", base, SNAPSHOT, "--", TASK, f".terminus/designs/{TASK}*", capture=True).splitlines()
    unexpected = sorted(set(changed) - set(FIX_PATHS))
    if unexpected:
        raise SystemExit("EC2 snapshot/main drift outside reviewed Q7 repair: " + ", ".join(unexpected))
    missing = sorted(set(FIX_PATHS) - set(changed))
    if missing:
        raise SystemExit("expected Q7 repair path no longer differs from main: " + ", ".join(missing))

    inv1, inv1p = compile_inv(INPUT_TASK, False, "01", EXPECTED_FIXED_INV)
    run("git", "checkout", SNAPSHOT, "--", *FIX_PATHS)
    run("git", "diff", "--check", "--", *FIX_PATHS)
    rec1 = record(inv1, inv1p, "FIXED", {
        "CHECKS": {
            "task_toml": "FIXED: reduced tags to six and replaced invalid network_mode=none with canonical public",
            "agent_image": "FIXED: canonical digest-pinned Go 1.24 image now includes tmux and asciinema",
            "dockerignore": "FIXED: added standard VCS/env/cache exclusions while retaining state/out/tmp exclusions",
            "verifier_image": "FIXED: separate verifier image now pre-creates declared artifact parent /app/enforcer",
            "test_sh": "PASS: binary reward file is assigned on normal pytest success/failure; current policy does not require trailing exit",
            "isolation": "PASS: agent build context is environment/ and does not include solution/ or tests/",
            "instruction_paths": "PASS: absolute /app/enforcer references and no private verifier path leakage",
            "task_lineage": f"FIXED task state is durably anchored at {SNAPSHOT_BRANCH}:{SNAPSHOT}; delta from {INPUT_TASK} is task/design scoped only",
        },
        "RERUN": "REQUIRED: Q7 repaired task-format files; recompile FORMAT_GATE against the committed repaired task snapshot and rerun format/build checks.",
    }, EXPECTED_FIXED_RECORD, "01")
    assert rec1["transition"]["action"] == "RETRY"

    run("python3", ".terminus/validate_task_complexity.py", TASK)
    run("python3", ".terminus/validate_environment_complexity.py", TASK)
    run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
    run("python3", ".terminus/validate_business_module_diversity.py", TASK)

    inv2, inv2p = compile_inv(SNAPSHOT, True, "02", EXPECTED_PASS_INV)
    rec2 = record(inv2, inv2p, "FORMAT_PASS", {
        "CHECKS": {
            "task_root_and_name": "PASS: flat Edition 3 task root and kebab-case name match task.toml",
            "task_toml": "PASS: version 2.0, six tags, top-level absolute artifact /app/enforcer, separate verifier, canonical public network mode and valid timeouts",
            "agent_image": "PASS: canonical digest-pinned Go 1.24 base with tmux/asciinema and clean apt transaction",
            "dockerignore": "PASS: non-trivial environment has VCS/env/cache/state/output exclusions",
            "verifier_image": "PASS: digest-pinned separate verifier; pytest dependencies baked; declared artifact parent /app/enforcer exists",
            "test_sh": "PASS: binary reward.txt assignment on success/failure, no runtime dependency install, canonical no-trailing-exit behavior",
            "solution_layout": "PASS: solution/solve.sh remains outside agent build context",
            "isolation": "PASS: solution/tests are not copied into environment image and no private .terminus files are inside task root",
            "instruction_paths": "PASS: solver references are absolute and public contracts remain under /app/enforcer",
            "complexity": "PASS: current strict task/environment complexity validators pass after format-only repair",
            "policy_conflicts": "PASS: none found",
            "task_lineage": f"PASS: retry consumes durable repaired task snapshot {SNAPSHOT}",
        },
        "RERUN": "PASS_AFTER_REPAIR: format-owned files were repaired and current structural/complexity/authenticity validators reran successfully; runtime/oracle remains mandatory at its later lifecycle checkpoint.",
    }, EXPECTED_PASS_RECORD, "02")
    assert rec2["transition"]["target"] == "ASSEMBLY"

    write_json(WORK / "integration.json", {"base_main": base, "task_snapshot": SNAPSHOT})
    print("Q7_INTEGRATION_REPLAY=PASS")


if __name__ == "__main__":
    main()
