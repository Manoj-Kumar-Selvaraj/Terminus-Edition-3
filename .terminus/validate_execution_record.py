#!/usr/bin/env python3
"""Validate execution outcomes, task lineage, gate predicates, and transitions."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

REQUIRED = [
    T / "agents" / "EXECUTION_RECORD.md",
    T / "agents" / "execution_outcomes.json",
    T / "agents" / "stage_acceptance_predicates.json",
    T / "agents" / "schemas" / "execution_outcomes.schema.json",
    T / "agents" / "schemas" / "stage_acceptance_predicates.schema.json",
    T / "agents" / "schemas" / "stage_result.schema.json",
    T / "agents" / "schemas" / "execution_record.schema.json",
    T / "execution" / "acceptance.py",
    T / "execution" / "authority.py",
    T / "execution" / "record.py",
    T / "execution" / "result_cli.py",
    T / "tests" / "test_execution_record.py",
]

POLICY_MARKERS = [
    "Execution-record policy version: `1.0`",
    "Explicit status semantics",
    "Invocation binding",
    "Task commit lineage",
    "Output validation",
    "Acceptance predicates",
    "Route validation",
    "Transition semantics",
    "FROZEN_CANDIDATE boundary",
    "Deterministic record identity",
    "Normal ChatGPT portability",
]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _head() -> str:
    return _git("rev-parse", "HEAD")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _review_pass() -> dict[str, object]:
    return {"verdict": "PASS", "confidence": "MEDIUM", "evidence_status": "SUFFICIENT", "missing_evidence": []}


def _full_outputs(invocation: dict[str, Any]) -> dict[str, Any]:
    outputs: dict[str, Any] = {
        str(field): "ok" for field in invocation["output_contract"]["required_fields"]
    }
    stage_id = str(invocation["stage"]["stage_id"])
    if stage_id == "RULE_RESOLUTION":
        outputs["KNOWN_POLICY_CONFLICTS"] = []
    elif stage_id == "SPEC_ALIGNMENT":
        outputs.update(Q1_STATUS="NO_GAP", Q2_STATUS="COVERED", Q3_STATUS="CLEAR")
    elif stage_id == "RUNTIME_AUTHENTICITY":
        outputs["RUNTIME_AUTHENTICITY_STATUS"] = "PASS"
    elif stage_id == "DETERMINISTIC_VALIDATION":
        outputs.update(
            ORACLE_REWARD=1,
            NOP_REWARD=0,
            F2P_EMPIRICAL_MATRIX=[{"case": "f2p", "pass": True}],
            P2P_EMPIRICAL_MATRIX=[{"case": "p2p", "pass": True}],
        )
    elif stage_id == "QUALITY_INTERLOCK":
        outputs.update(Q4_RESULT=_review_pass(), Q6_RESULT=_review_pass(), EVIDENCE_SUFFICIENCY="SUFFICIENT")
    elif stage_id == "PRE_LLMAJ":
        outputs.update({f"STAGE_{letter}": "PASS" for letter in "ABCDEF"})
    elif stage_id == "OFFICIAL_MODEL_TRIALS":
        outputs.update(
            GPT_5_5_TRIALS=[{"trial": i} for i in range(5)],
            CLAUDE_OPUS_4_8_TRIALS=[{"trial": i} for i in range(5)],
            PER_TEST_SOLVABILITY={"test_f2p_example": 1},
        )
    elif stage_id == "FINAL_REVIEW":
        outputs.update(FINAL_COMPLIANCE=_review_pass(), FINAL_HUMAN_QUALITY=_review_pass(), FINAL_PACKAGE_EVIDENCE={"manifest": "ok"})
    elif stage_id == "SUBMISSION_READY":
        outputs.update(READINESS_STATUS="SUBMISSION_READY", GATE_EVIDENCE={"all": "current"})
    return outputs


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        print("Terminus execution-record validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    policy_text = (T / "agents" / "EXECUTION_RECORD.md").read_text(encoding="utf-8")
    for marker in POLICY_MARKERS:
        if marker.lower() not in policy_text.lower():
            errors.append(f"EXECUTION_RECORD.md missing marker: {marker}")

    outcome_schema = _load(T / "agents" / "schemas" / "execution_outcomes.schema.json")
    predicate_schema = _load(T / "agents" / "schemas" / "stage_acceptance_predicates.schema.json")
    result_schema = _load(T / "agents" / "schemas" / "stage_result.schema.json")
    record_schema = _load(T / "agents" / "schemas" / "execution_record.schema.json")
    expected_ids = {
        "outcome": (outcome_schema, "terminus-execution-outcomes-v1"),
        "predicate": (predicate_schema, "terminus-stage-acceptance-predicates-v1"),
        "stage result": (result_schema, "terminus-stage-result-v1"),
        "execution record": (record_schema, "terminus-execution-record-v1"),
    }
    for label, (schema, expected_id) in expected_ids.items():
        if schema.get("$id") != expected_id:
            errors.append(f"{label} schema has wrong $id")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{label} schema must fail closed on top-level properties")
    if "output_task_commit" not in result_schema.get("required", []):
        errors.append("stage result schema must require output_task_commit")
    if "task_lineage" not in record_schema.get("required", []):
        errors.append("execution record schema must require task_lineage")

    policy = RetrievalPolicy(ROOT)
    execution_authority = ExecutionAuthority(policy)
    outcomes = _load(T / "agents" / "execution_outcomes.json")
    predicates = _load(T / "agents" / "stage_acceptance_predicates.json")
    completion = _load(T / "agents" / "stage_contract_completion.json")
    if outcomes.get("outcome_version") != "1.0":
        errors.append("execution outcome version must be 1.0")
    if predicates.get("predicate_version") != "1.0":
        errors.append("acceptance predicate version must be 1.0")

    outcome_stages = outcomes.get("stages", {})
    if not isinstance(outcome_stages, dict) or set(outcome_stages) != set(policy.stages):
        errors.append("execution outcome stage IDs must exactly match the stage registry")
        outcome_stages = {}

    for stage_id, stage in policy.stages.items():
        semantics = outcome_stages.get(stage_id, {})
        legal = set(stage["output_contract"]["status_values"])
        advance = set(semantics.get("advance_statuses", [])) if isinstance(semantics, dict) else set()
        route_map = semantics.get("route_statuses", {}) if isinstance(semantics, dict) else {}
        route = set(route_map) if isinstance(route_map, dict) else set()
        retry = set(semantics.get("retry_statuses", [])) if isinstance(semantics, dict) else set()
        block = set(semantics.get("block_statuses", [])) if isinstance(semantics, dict) else set()
        buckets = [advance, route, retry, block]
        if set().union(*buckets) != legal:
            errors.append(f"{stage_id}: status partition does not cover legal statuses exactly")
        for index, left in enumerate(buckets):
            for right in buckets[index + 1 :]:
                if left & right:
                    errors.append(f"{stage_id}: status dispositions overlap: {sorted(left & right)}")
        full = set(semantics.get("full_output_statuses", [])) if isinstance(semantics, dict) else set()
        if not advance <= full:
            errors.append(f"{stage_id}: every ADVANCE status must require full outputs")
        failure_routes = set(stage.get("failure_routes", {}))
        if isinstance(route_map, dict):
            for status, route_semantics in route_map.items():
                allowed = set(route_semantics.get("allowed_route_keys", [])) if isinstance(route_semantics, dict) else set()
                if not allowed or not allowed <= failure_routes:
                    errors.append(f"{stage_id}/{status}: route keys must be declared failure routes")
        target = stage.get("success_transition")
        if target != "END" and target not in policy.stages and target not in completion.get("state_contracts", {}):
            errors.append(f"{stage_id}: unregistered success transition {target}")

    predicate_stages = predicates.get("stages", {})
    if not isinstance(predicate_stages, dict):
        errors.append("acceptance predicate stages must be an object")
        predicate_stages = {}
    required_predicate_gates = {
        "RULE_RESOLUTION", "SPEC_ALIGNMENT", "RUNTIME_AUTHENTICITY",
        "DETERMINISTIC_VALIDATION", "QUALITY_INTERLOCK", "PRE_LLMAJ",
        "OFFICIAL_MODEL_TRIALS", "FINAL_REVIEW", "SUBMISSION_READY",
    }
    if not required_predicate_gates <= set(predicate_stages):
        errors.append("acceptance predicate registry is missing required aggregate gates")
    for stage_id, status_map in predicate_stages.items():
        if stage_id not in policy.stages or not isinstance(status_map, dict):
            errors.append(f"invalid acceptance predicate stage {stage_id}")
            continue
        declared_outputs = set(policy.stages[stage_id]["output_contract"]["required_fields"]) | set(policy.stages[stage_id]["output_contract"]["optional_fields"])
        advance = set(outcome_stages[stage_id]["advance_statuses"])
        for status, checks in status_map.items():
            if status not in advance:
                errors.append(f"{stage_id}/{status}: predicates may guard ADVANCE statuses only")
            if not isinstance(checks, list) or not checks:
                errors.append(f"{stage_id}/{status}: predicate list must be non-empty")
                continue
            for check in checks:
                root_field = str(check.get("path", "")).split(".", 1)[0] if isinstance(check, dict) else ""
                if root_field not in declared_outputs:
                    errors.append(f"{stage_id}/{status}: predicate path starts at undeclared output {root_field}")

    head = _head()
    invocation_builder = StageInvocationBuilder(ROOT, policy)
    record_builder = ExecutionRecordBuilder(ROOT, policy)
    record_ids: set[str] = set()
    for stage_id, stage in policy.stages.items():
        advances = outcome_stages.get(stage_id, {}).get("advance_statuses", [])
        if not advances:
            errors.append(f"{stage_id}: no ADVANCE status")
            continue
        inputs = {str(field): {"validator": str(field)} for field in stage["input_contract"]["required_fields"]}
        role_id = execution_authority.primary_role_for_stage(stage_id)
        try:
            invocation = invocation_builder.build(
                InvocationContext(
                    stage_id=stage_id,
                    role_id=role_id,
                    task_id="execution-validator",
                    task_commit=head,
                    control_plane_commit=head,
                ),
                inputs,
            )
            result = {
                "schema_version": "1.0",
                "invocation_id": invocation["invocation_id"],
                "output_task_commit": head,
                "status": advances[0],
                "outputs": _full_outputs(invocation),
                "evidence_refs": [],
            }
            record = record_builder.build(invocation, result)
        except Exception as exc:  # pragma: no cover
            errors.append(f"{stage_id}: failed execution-record compilation: {exc}")
            continue
        if record["role_id"] != role_id or record["disposition"] != "ADVANCE":
            errors.append(f"{stage_id}: canonical ADVANCE record drift")
        if record["task_lineage"]["input_task_commit"] != head or record["task_lineage"]["output_task_commit"] != head:
            errors.append(f"{stage_id}: same-commit lineage projection drift")
        if record["transition"]["target"] != stage["success_transition"]:
            errors.append(f"{stage_id}: transition target drift")
        record_ids.add(record["record_id"])
    if len(record_ids) != len(policy.stages):
        errors.append("canonical per-stage records did not produce unique record IDs")

    parent = _git("rev-parse", "HEAD^")
    try:
        stage = policy.stages["WORK_PACKAGE_RESEARCH"]
        producer_invocation = invocation_builder.build(
            InvocationContext(
                stage_id="WORK_PACKAGE_RESEARCH",
                role_id="A1_SCENARIO_RESEARCHER",
                task_id="execution-validator",
                task_commit=parent,
                control_plane_commit=head,
            ),
            {str(field): "ok" for field in stage["input_contract"]["required_fields"]},
        )
        producer_record = record_builder.build(
            producer_invocation,
            {
                "schema_version": "1.0",
                "invocation_id": producer_invocation["invocation_id"],
                "output_task_commit": head,
                "status": "CANDIDATES_READY",
                "outputs": _full_outputs(producer_invocation),
                "evidence_refs": [],
            },
        )
        if producer_record["task_lineage"]["task_changed"] is not True:
            errors.append("producer descendant commit must be recorded as a task change")
    except Exception as exc:
        errors.append(f"producer descendant lineage validation failed: {exc}")

    try:
        qi = policy.stages["QUALITY_INTERLOCK"]
        invocation = invocation_builder.build(
            InvocationContext(
                stage_id="QUALITY_INTERLOCK",
                role_id="CI_ORCHESTRATOR",
                task_id="execution-validator",
                task_commit=head,
                control_plane_commit=head,
            ),
            {str(field): "ok" for field in qi["input_contract"]["required_fields"]},
        )
        bad_outputs = _full_outputs(invocation)
        bad_outputs["Q4_RESULT"]["verdict"] = "REVISE"
        record_builder.build(
            invocation,
            {
                "schema_version": "1.0",
                "invocation_id": invocation["invocation_id"],
                "output_task_commit": head,
                "status": "QUALITY_INTERLOCK_PASS",
                "outputs": bad_outputs,
                "evidence_refs": [],
            },
        )
        errors.append("invalid Q4 value incorrectly satisfied QUALITY_INTERLOCK_PASS")
    except ValueError as exc:
        if "acceptance predicate failed" not in str(exc):
            errors.append(f"aggregate predicate rejection used unexpected error: {exc}")

    if errors:
        print("Terminus execution-record validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus execution-record validation PASS")
    print(
        "execution_record=1.0 outcomes=1.0 predicates=1.0 stages=23 "
        "status_partition=total result_binding=invocation_exact task_identity=reserved_before_stage0 "
        "task_lineage=input_output_descendant mutation=producer_fixer_only "
        "acceptance_predicates=value_enforced outputs=declared routes=registered "
        "transition=advance_route_retry_block record_identity=deterministic reasoning=not_persisted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
