#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
CONTROL = "215cc70bcebcccc3c9a401af1b74a97d90026da3"
TASK_COMMIT = "0ad08868799c19ea2e02458bd2fc92ec64eaa288"
WORK = pathlib.Path(os.environ["RUNNER_TEMP"]) / "ec2-assembly-a10"
WORK.mkdir(parents=True, exist_ok=True)


def run(*args, capture=False):
    if capture:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    subprocess.run(args, cwd=ROOT, check=True)


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def compile_stage(expected_stage, expected_mode, inputs, label):
    ip = WORK / f"{label}-inputs.json"
    cp = WORK / f"{label}-continue.json"
    write_json(ip, inputs)
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", TASK_COMMIT,
        "--control-plane-commit", CONTROL,
        "--inputs-json", str(ip), "--output", str(cp))
    payload = json.loads(cp.read_text())
    if payload.get("next", {}).get("stage_id") != expected_stage:
        raise SystemExit(f"expected {expected_stage}, got {payload.get('next')}")
    if payload.get("execution_mode") != expected_mode:
        raise SystemExit(f"{expected_stage} mode expected={expected_mode} actual={payload.get('execution_mode')}")
    inv = payload.get("invocation")
    if not isinstance(inv, dict) or inv.get("readiness") != "READY":
        raise SystemExit(f"{expected_stage} invocation is not READY")
    p = WORK / f"{label}-invocation.json"
    write_json(p, inv)
    print(f"{expected_stage}_INVOCATION={inv['invocation_id']}")
    return inv, p


def record(inv, inv_path, status, outputs, label, expected_target):
    rp = WORK / f"{label}-result.json"
    op = WORK / f"{label}-record.json"
    write_json(rp, {
        "schema_version": "1.0",
        "invocation_id": inv["invocation_id"],
        "output_task_commit": TASK_COMMIT,
        "status": status,
        "outputs": outputs,
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{TASK_COMMIT}"},
            {"kind": "COMMIT", "ref": f"commit:{CONTROL}"},
        ],
    })
    run("python3", ".terminus/execution/controller_cli.py", "record",
        "--invocation", str(inv_path), "--result", str(rp), "--output", str(op))
    rec = json.loads(op.read_text())["record"]
    if rec["transition"].get("target") != expected_target:
        raise SystemExit(f"{inv['stage']['stage_id']} target drift: {rec['transition']}")
    print(f"RECORDED {inv['stage']['stage_id']} status={status} record={rec['record_id']}")
    return rec


def assembly_inputs():
    return {
        "CURRENT_TASK": {
            "root": TASK,
            "task_commit": TASK_COMMIT,
            "environment_root": f"{TASK}/environment/enforcer",
            "instruction_path": f"{TASK}/instruction.md",
            "language_runtime": "Go policy enforcement runtime",
            "runtime_artifact": "/app/enforcer",
            "substantive_loc": 4096,
            "top_level": [".gitattributes", "README.md", "environment/", "instruction.md", "solution/", "task.toml", "tests/"],
            "acquisition_surfaces": ["package", "container", "dependency"],
            "durable_state": ["cache", "audit journal", "last-decision projection", "permit replay consumption"],
        },
        "CURRENT_ORACLE": {
            "status": "IMPLEMENTED",
            "task_commit": TASK_COMMIT,
            "entrypoint": f"{TASK}/solution/solve.sh",
            "solution_tree": f"{TASK}/solution/files/",
            "empirical_oracle_status": "not yet re-earned; mandatory DETERMINISTIC_VALIDATION remains downstream",
            "restored_invariants": [
                "uniform source/digest prerequisites across package/container/dependency managers",
                "current scanner evidence and digest/policy/DB/TTL-bound cache reuse",
                "exact current vulnerability exceptions that cannot bypass prerequisites",
                "secret-keyed exact-scope permits with optional durable single-use replay enforcement",
                "durable ALLOW/DENY journal before derived projection",
                "restart/concurrency-safe recovery, replay and idempotent retry",
            ],
        },
        "CURRENT_VERIFIER": {
            "status": "VERIFIER_READY",
            "F2P_COUNT": 27,
            "P2P_COUNT": 9,
            "requirement_families": [
                "source/digest policy", "scanner/cache freshness", "vulnerability exception scope",
                "permit authentication/replay", "audit durability/recovery", "preservation/CLI compatibility",
            ],
            "edge_boundary_coverage": [
                "manager bypass and missing digest", "scanner DB/policy/TTL/digest cache invalidation",
                "exception expiry/scope/prerequisite ordering", "permit secret/instance/restart/concurrent replay",
                "audit unterminated-tail/corruption/idempotent retry",
            ],
            "negative_failure_coverage": [
                "untrusted source", "missing digest", "scanner unavailable/stale/corrupt evidence",
                "wrong/expired exception", "permit tamper/scope/replay", "corrupt audit history",
            ],
            "test_independence": "public CLI/output/durable-state assertions; no solution import or private implementation dependency",
        },
        "SPEC_ALIGNMENT_STATUS": {"status": "ALIGNED", "Q1_STATUS": "NO_GAP", "Q2_STATUS": "COVERED", "Q3_STATUS": "CLEAR"},
        "FORMAT_STATUS": {
            "status": "FORMAT_PASS",
            "task_commit": TASK_COMMIT,
            "checks": "task metadata, public network mode, canonical agent image/tooling, verifier artifact parent, dockerignore, isolation and instruction paths pass",
            "repair_recorded": True,
        },
        "PRIVATE_TEST_MAP": {"classification": "27 F2P + 9 P2P", "empirical_status": "runtime/oracle deferred to DETERMINISTIC_VALIDATION"},
        "PRIVATE_DEFECT_GRAPH": {"manifestations": 26, "root_cause_clusters": 6, "causal_edges": 37, "cross_cluster_pairs": 11, "connected_manifestations": 26},
    }


def complexity_inputs():
    instruction = (ROOT / TASK / "instruction.md").read_text()
    return {
        "ENVIRONMENT_TREE": {
            "root": f"{TASK}/environment/enforcer",
            "entrypoints": ["artifactguard evaluate", "artifactguard verify-permit"],
            "major_components": [
                "cmd/artifactguard", "internal/core", "internal/platform identity/policy",
                "scanner/cache", "exceptions", "permit/replay", "audit/state/recovery",
                "package/container/dependency control catalogs",
            ],
        },
        "SUBSTANTIVE_LOC_REPORT": {
            "substantive_loc": 4096,
            "validator": ".terminus/validate_task_complexity.py",
            "largest_reachable_modules": [
                "catalog_package.go:1203", "catalog_dependency.go:1003", "catalog_container.go:803",
                "cmd/artifactguard/main.go:153", "platform/types.go:112", "platform/engine.go:96",
            ],
        },
        "DEFECT_GRAPH": {
            "profile": "large_system_strict", "defect_manifestations": 26,
            "connected_manifestations": 26, "root_cause_clusters": 6,
            "causal_edges": 37, "cross_cluster_pairs": 11,
            "clusters": [
                "canonical identity", "evidence freshness", "exception ordering/scope",
                "permit authentication/scope", "audit durability", "recovery/concurrency",
            ],
        },
        "TEST_CLASSIFICATION_MAP": {
            "F2P_COUNT": 27, "P2P_COUNT": 9, "requirements": 6,
            "F2P_BY_REQUIREMENT": {
                "REQ_SOURCE_DIGEST": 4, "REQ_EVIDENCE_CACHE": 7, "REQ_EXCEPTION_SCOPE": 5,
                "REQ_PERMIT_AUTH_REPLAY": 6, "REQ_AUDIT_RECOVERY": 5,
            },
            "P2P_SCOPE": "healthy allow/deny, exact exception, current cache, stateless permit compatibility and fixture preservation",
        },
        "RUNTIME_REACHABILITY_EVIDENCE": [
            "evaluate reaches normalization, canonical identity/source/digest prerequisites, scanner/cache, exception, permit, projection and audit paths",
            "verify-permit reaches authentication, exact scope, expiry and optional durable replay state",
            "package/container/dependency catalog modules are reached through live ApplicableRules selection",
        ],
        "PRODUCTION_CHARACTERISTIC_EVIDENCE": [
            "one Go admission runtime spans OS packages, OCI containers and build dependencies",
            "stable public evaluate/verify-permit CLI with durable caller-provided state",
            "versioned source/digest policy and reusable vulnerability evidence cache",
            "scoped exceptions, keyed permits, replay ledger and append-only decision audit",
            "manager/surface/environment control catalogs rather than one-off fixtures",
            "deterministic local scanner/policy/exception fixtures without required network dependency",
        ],
        "INSTRUCTION": instruction,
    }


def main():
    base = run("git", "rev-parse", "HEAD", capture=True)
    control_path = WORK / "control.json"
    run("python3", ".terminus/execution/controller_cli.py", "control-plane", "--head", base, "--output", str(control_path))
    if json.loads(control_path.read_text())["control_plane_commit"] != CONTROL:
        raise SystemExit("effective control changed before assembly/A10")

    # Assembly-local deterministic evidence.
    run("git", "diff", "--check", "--", TASK)
    run("python3", ".terminus/validate_task_complexity.py", TASK)

    inv, invp = compile_stage("ASSEMBLY", "INLINE_SPECIALIST", assembly_inputs(), "01-assembly")
    record(inv, invp, "ASSEMBLED", {
        "TASK_COMMIT": TASK_COMMIT,
        "STRUCTURE": {
            "task_root": TASK, "runtime_artifact": "/app/enforcer", "separate_verifier": True,
            "required_top_level": ["task.toml", "instruction.md", "README.md", "environment/", "tests/", "solution/"],
            "acquisition_surfaces": 3,
        },
        "INSTRUCTION_SHAPE": "PASS: direct EC2/platform-security repair request with absolute /app/enforcer and public contract references; no private test enumeration.",
        "INSTRUCTION_REQUIREMENT_COMPLETENESS": "PASS: Q1 NO_GAP, Q2 COVERED and Q3 CLEAR across source/digest, evidence freshness, exception scope, permits/replay, audit/recovery and preservation.",
        "INSTRUCTION_DOC_BOUNDARY": "PASS: governing semantics are in solver-visible policy/state/operations docs; private defect/test/oracle evidence remains outside solver-facing material.",
        "SUBSTANTIVE_REACHABLE_LOC_EVIDENCE": {"substantive_loc": 4096, "runtime_entrypoint": "environment/enforcer/cmd/artifactguard/main.go", "major_components": ["internal/core", "internal/platform", "package/container/dependency catalogs", "scanner/cache", "permit/replay", "audit/state"]},
        "PRODUCTION_CHARACTERISTIC_EVIDENCE": ["shared cross-manager admission policy", "durable scanner/cache and decision state", "scoped exceptions", "secret-keyed permits with replay boundary", "append-only audit and recovery", "stable CLI and deterministic fixtures"],
        "F2P_ORGANICITY_EVIDENCE": "27 F2P cases are distinct externally observable security/state transitions across five coupled repair families; 9 P2P cases protect preserved healthy behavior.",
        "EDGE_BOUNDARY_COVERAGE_EVIDENCE": ["missing/mutable digest identity", "policy/scanner revision and TTL boundaries", "exception expiry/scope", "permit expiry/instance/replay concurrency", "audit tail/corruption/idempotent retry"],
        "NEGATIVE_FAILURE_COVERAGE_EVIDENCE": ["untrusted source", "missing digest", "scanner unavailable/stale/corrupt", "wrong/expired exception", "permit tamper/scope/replay", "corrupt durable history"],
        "LEAKAGE_CHECK": "PASS: environment image excludes solution/tests; instruction/README expose no private defect IDs, hidden tests, oracle outcomes or model-trial evidence.",
        "STATIC_CHECKS": "PASS: Q7 format checks and strict task-complexity validation are current; runtime/oracle is intentionally deferred to its registered checkpoint.",
        "NEXT_GATE": "COMPLEXITY_GATE",
    }, "01-assembly", "COMPLEXITY_GATE")

    # A10 same-chat semantic governor + mandatory strict validator.
    run("python3", ".terminus/validate_task_complexity.py", TASK)
    inv2, inv2p = compile_stage("COMPLEXITY_GATE", "INLINE_SPECIALIST", complexity_inputs(), "02-a10")
    record(inv2, inv2p, "PASS", {
        "SUBSTANTIVE_LOC": 4096,
        "REACHABLE_PRODUCTION_LOC": 4096,
        "PRODUCTION_CHARACTERISTICS": ["shared package/container/dependency admission runtime", "durable security state", "versioned policy/evidence cache", "exact-scope exceptions/permits", "restart/concurrency recovery", "stable operational CLI"],
        "DEFECT_MANIFESTATIONS": 26,
        "CONNECTED_MANIFESTATIONS": 26,
        "ROOT_CAUSE_CLUSTERS": 6,
        "F2P_COUNT": 27,
        "P2P_COUNT": 9,
        "F2P_ORGANICITY": "PASS: cases represent separate policy, freshness, scope, replay, durability and recovery transitions rather than parameter-renamed copies.",
        "EDGE_BOUNDARY_COVERAGE": "PASS: digest mutation, revisions, TTL/expiry, scope mismatches, restart, concurrent replay, audit corruption and idempotent retry are covered.",
        "NEGATIVE_FAILURE_COVERAGE": "PASS: fail-closed source/digest/scanner/exception/permit/audit failure modes are represented.",
        "PADDING_RISK": "LOW: high LOC concentration is in live manager control catalogs and policy runtime reached from public commands; no dead filler is required to satisfy scale.",
        "TEST_DUPLICATION_RISK": "LOW: 27 F2P probes map to distinct observable transitions across five coupled families; 9 P2P cases protect different preserved behaviors.",
        "INSTRUCTION_CHECKLIST_RISK": "LOW: the two-paragraph engineering request groups invariants by operational policy rather than enumerating verifier cases.",
        "REQUIRED_CHANGES": [],
    }, "02-a10", "RUNTIME_AUTHENTICITY")

    # Preview exact machine routing for the next controller stage.
    preview_inputs = {
        "CURRENT_TASK": {"task_id": TASK, "task_commit": TASK_COMMIT, "environment_root": f"{TASK}/environment/enforcer"},
        "PRODUCTION_CHARACTERISTIC_EVIDENCE": ["shared production-shaped policy runtime", "durable cache/audit/replay state", "live package/container/dependency control catalogs"],
    }
    pp = WORK / "03-runtime-inputs.json"
    po = WORK / "03-runtime-preview.json"
    write_json(pp, preview_inputs)
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", TASK_COMMIT,
        "--control-plane-commit", CONTROL, "--inputs-json", str(pp), "--output", str(po))
    preview = json.loads(po.read_text())
    print("NEXT_STAGE=" + str(preview.get("next", {}).get("stage_id")))
    print("NEXT_MODE=" + str(preview.get("execution_mode")))


if __name__ == "__main__":
    main()
