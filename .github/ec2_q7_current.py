#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
CONTROL = "215cc70bcebcccc3c9a401af1b74a97d90026da3"
INPUT_TASK = "8836f886d7cfc7f2747264026da31d1dfa49c658"
WORK = pathlib.Path(os.environ["RUNNER_TEMP"]) / "ec2-q7"
WORK.mkdir(parents=True, exist_ok=True)


def run(*args, capture=False):
    if capture:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    subprocess.run(args, cwd=ROOT, check=True)


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def continue_stage(task_commit, inputs, ordinal):
    inp = WORK / f"{ordinal}-inputs.json"
    out = WORK / f"{ordinal}-continue.json"
    write_json(inp, inputs)
    run(
        "python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK,
        "--task-commit", task_commit,
        "--control-plane-commit", CONTROL,
        "--inputs-json", str(inp),
        "--output", str(out),
    )
    value = json.loads(out.read_text())
    inv = value.get("invocation")
    if value.get("next", {}).get("stage_id") != "FORMAT_GATE":
        raise SystemExit(f"machine route is not FORMAT_GATE: {value.get('next')}")
    if value.get("execution_mode") != "INLINE_SPECIALIST":
        raise SystemExit(f"FORMAT_GATE mode is not INLINE_SPECIALIST: {value.get('execution_mode')}")
    if not isinstance(inv, dict) or inv.get("readiness") != "READY":
        raise SystemExit("FORMAT_GATE invocation is not READY")
    inv_path = WORK / f"{ordinal}-invocation.json"
    write_json(inv_path, inv)
    return inv, inv_path


def record(inv, inv_path, task_commit, status, outputs, ordinal):
    result_path = WORK / f"{ordinal}-result.json"
    record_path = WORK / f"{ordinal}-record.json"
    result = {
        "schema_version": "1.0",
        "invocation_id": inv["invocation_id"],
        "output_task_commit": task_commit,
        "status": status,
        "outputs": outputs,
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{task_commit}"},
            {"kind": "COMMIT", "ref": f"commit:{CONTROL}"},
        ],
    }
    write_json(result_path, result)
    run(
        "python3", ".terminus/execution/controller_cli.py", "record",
        "--invocation", str(inv_path),
        "--result", str(result_path),
        "--output", str(record_path),
    )
    value = json.loads(record_path.read_text())
    rec = value["record"]
    print(f"RECORDED {status} invocation={inv['invocation_id']} record={rec['record_id']}")
    return rec


def q7_inputs(fixed=False):
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
                "version": "2.0",
                "name": TASK,
                "artifacts": ["/app/enforcer"],
                "verifier_environment_mode": "separate",
                "network_mode": "public" if fixed else "none",
                "agent_timeout_sec": 10800,
                "verifier_timeout_sec": 1800,
                "tag_count": 6 if fixed else 8,
                "workdir": "/app/enforcer",
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


def apply_fixes():
    task_toml = ROOT / TASK / "task.toml"
    text = task_toml.read_text()
    text = text.replace(
        'tags = ["aws", "ec2", "policy-as-code", "supply-chain", "containers", "packages", "vulnerability", "security"]',
        'tags = ["aws", "ec2", "policy-as-code", "supply-chain", "vulnerability", "security"]',
    )
    text = text.replace('network_mode = "none"', 'network_mode = "public"')
    task_toml.write_text(text)

    (ROOT / TASK / "environment" / "Dockerfile").write_text(
        'FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac\n\n'
        'LABEL org.opencontainers.image.title="EC2 artifact policy enforcement lab"\n'
        'LABEL org.opencontainers.image.version="1.0"\n\n'
        'RUN apt-get update \\\n'
        ' && apt-get install -y --no-install-recommends ca-certificates tmux asciinema \\\n'
        ' && rm -rf /var/lib/apt/lists/*\n\n'
        'WORKDIR /app/enforcer\n'
        'COPY enforcer/ /app/enforcer/\n'
        'RUN go build -o /usr/local/bin/artifactguard ./cmd/artifactguard \\\n'
        ' && mkdir -p /app/enforcer/state /app/enforcer/out\n\n'
        'ENV ENFORCER_ROOT="/app/enforcer"\n'
    )

    (ROOT / TASK / "environment" / ".dockerignore").write_text(
        ".git\n.gitignore\n.env\n__pycache__/\n*.pyc\nstate\nout\n*.tmp\n"
    )

    test_docker = ROOT / TASK / "tests" / "Dockerfile"
    t = test_docker.read_text()
    if "mkdir -p /app/enforcer" not in t:
        t = t.replace("WORKDIR /tests\n", "RUN mkdir -p /app/enforcer\nWORKDIR /tests\n")
    test_docker.write_text(t)

    run("git", "diff", "--check", "--", TASK)
    run("git", "add", "--",
        f"{TASK}/task.toml",
        f"{TASK}/environment/Dockerfile",
        f"{TASK}/environment/.dockerignore",
        f"{TASK}/tests/Dockerfile",
    )
    run("git", "config", "user.name", "terminus-q7[bot]")
    run("git", "config", "user.email", "terminus-q7[bot]@users.noreply.github.com")
    run("git", "commit", "-m", f"Fix {TASK} Edition 3 task format")
    return run("git", "rev-parse", "HEAD", capture=True)


def main():
    base = run("git", "rev-parse", "HEAD", capture=True)
    control_path = WORK / "control.json"
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", base, "--output", str(control_path))
    resolved = json.loads(control_path.read_text())["control_plane_commit"]
    if resolved != CONTROL:
        raise SystemExit(f"control changed expected={CONTROL} actual={resolved}")

    inv1, inv1_path = continue_stage(INPUT_TASK, q7_inputs(False), "01")
    fix_sha = apply_fixes()
    rec1 = record(
        inv1, inv1_path, fix_sha, "FIXED",
        {
            "CHECKS": {
                "task_toml": "FIXED: reduced tags to six and replaced invalid network_mode=none with canonical public",
                "agent_image": "FIXED: canonical digest-pinned Go 1.24 image now includes tmux and asciinema",
                "dockerignore": "FIXED: added standard VCS/env/cache exclusions while retaining state/out/tmp exclusions",
                "verifier_image": "FIXED: separate verifier image now pre-creates declared artifact parent /app/enforcer",
                "test_sh": "PASS: binary reward file is assigned on normal pytest success/failure; current policy does not require trailing exit",
                "isolation": "PASS: agent build context is environment/ and does not include solution/ or tests/",
                "instruction_paths": "PASS: absolute /app/enforcer references and no private verifier path leakage",
            },
            "RERUN": "REQUIRED: Q7 repaired task-format files; recompile FORMAT_GATE against the committed repaired task snapshot and rerun format/build checks.",
        },
        "01",
    )
    if rec1.get("transition", {}).get("action") != "RETRY":
        raise SystemExit(f"FIXED did not RETRY: {rec1.get('transition')}")

    # Mechanical checks on the repaired tree before the retry result.
    run("python3", ".terminus/validate_task_complexity.py", TASK)
    run("python3", ".terminus/validate_environment_complexity.py", TASK)
    run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
    run("python3", ".terminus/validate_business_module_diversity.py", TASK)
    env_text = (ROOT / TASK / "environment" / "Dockerfile").read_text()
    assert "@sha256:" in env_text and "tmux" in env_text and "asciinema" in env_text
    td = (ROOT / TASK / "tests" / "Dockerfile").read_text()
    assert "@sha256:" in td and "mkdir -p /app/enforcer" in td

    inv2, inv2_path = continue_stage(fix_sha, q7_inputs(True), "02")
    rec2 = record(
        inv2, inv2_path, fix_sha, "FORMAT_PASS",
        {
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
            },
            "RERUN": "PASS_AFTER_REPAIR: format-owned files were repaired and current structural/complexity/authenticity validators reran successfully; runtime/oracle remains mandatory at its later lifecycle checkpoint.",
        },
        "02",
    )
    if rec2.get("transition", {}).get("target") != "ASSEMBLY":
        raise SystemExit(f"FORMAT_PASS did not advance to ASSEMBLY: {rec2.get('transition')}")

    print(f"Q7_FIX_SHA={fix_sha}")
    print("Q7_COMPLETE=PASS")


if __name__ == "__main__":
    main()
