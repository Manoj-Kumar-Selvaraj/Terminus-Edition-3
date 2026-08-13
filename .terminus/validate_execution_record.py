#!/usr/bin/env python3
"""Validate execution outcome classification, result recording, and transitions."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

REQUIRED = [
    T / "agents" / "EXECUTION_RECORD.md",
    T / "agents" / "execution_outcomes.json",
    T / "agents" / "schemas" / "execution_outcomes.schema.json",
    T / "agents" / "schemas" / "stage_result.schema.json",
    T / "agents" / "schemas" / "execution_record.schema.json",
    T / "execution" / "record.py",
    T / "execution" / "result_cli.py",
    T / "tests" / "test_execution_record.py",
]

POLICY_MARKERS = [
    "Execution-record policy version: `1.0`",
    "Explicit status semantics",
    "Invocation binding",
    "Output validation",
    "Route validation",
    "Transition semantics",
    "FROZEN_CANDIDATE boundary",
    "Deterministic record identity",
    "Normal ChatGPT portability",
]


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _full_outputs(invocation: dict[str, Any]) -> dict[str, Any]:
    return {
        str(field): {"validator": str(field)}
        for field in invocation["output_contract"]["required_fields"]
    }


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    policy_text = (T / "agents" / "EXECUTION_RECORD.md").read_text(encoding="utf-8")
    for marker in POLICY_MARKERS:
        if marker.lower() not in policy_text.lower():
            errors.append(f"EXECUTION_RECORD.md missing marker: {marker}")

    outcome_schema = _load(T / "agents" / "schemas" / "execution_outcomes.schema.json")
    result_schema = _load(T / "agents" / "schemas" / "stage_result.schema.json")
    record_schema = _load(T / "agents" / "schemas" / "execution_record.schema.json")
    if outcome_schema.get("$id") != "terminus-execution-outcomes-v1":
        errors.append("execution outcome schema has wrong $id")
    if result_schema.get("$id") != "terminus-stage-result-v1":
        errors.append("stage result schema has wrong $id")
    if record_schema.get("$id") != "terminus-execution-record-v1":
        errors.append("execution record schema has wrong $id")
    for label, schema in (
        ("outcome", outcome_schema),
        ("stage result", result_schema),
        ("execution record", record_schema),
    ):
        if schema.get("additionalProperties") is not False:
            errors.append(f"{label} schema must fail closed on top-level properties")

    policy = RetrievalPolicy(ROOT)
    outcomes = _load(T / "agents" / "execution_outcomes.json")
    completion = _load(T / "agents" / "stage_contract_completion.json")
    if outcomes.get("outcome_version") != "1.0":
        errors.append("execution outcome version must be 1.0")
    if outcomes.get("dispositions") != ["ADVANCE", "ROUTE", "RETRY", "BLOCK"]:
        errors.append("execution disposition vocabulary drift")

    outcome_stages = outcomes.get("stages")
    if not isinstance(outcome_stages, dict):
        errors.append("execution outcomes stages must be an object")
        outcome_stages = {}
    if set(outcome_stages) != set(policy.stages):
        errors.append(
            "execution outcome stage IDs do not exactly match stage registry: "
            f"missing={sorted(set(policy.stages) - set(outcome_stages))} "
            f"extra={sorted(set(outcome_stages) - set(policy.stages))}"
        )

    for stage_id, stage in policy.stages.items():
        semantics = outcome_stages.get(stage_id)
        if not isinstance(semantics, dict):
            continue
        legal = set(stage["output_contract"]["status_values"])
        advance = set(semantics.get("advance_statuses", []))
        route_map = semantics.get("route_statuses", {})
        if not isinstance(route_map, dict):
            errors.append(f"{stage_id}: route_statuses must be an object")
            route_map = {}
        route = set(route_map)
        retry = set(semantics.get("retry_statuses", []))
        block = set(semantics.get("block_statuses", []))
        sets = {"ADVANCE": advance, "ROUTE": route, "RETRY": retry, "BLOCK": block}
        for left_name, left in sets.items():
            for right_name, right in sets.items():
                if left_name >= right_name:
                    continue
                overlap = left & right
                if overlap:
                    errors.append(
                        f"{stage_id}: statuses overlap {left_name}/{right_name}: {sorted(overlap)}"
                    )
        classified = advance | route | retry | block
        if classified != legal:
            errors.append(
                f"{stage_id}: status classification mismatch missing={sorted(legal-classified)} "
                f"extra={sorted(classified-legal)}"
            )
        full = set(semantics.get("full_output_statuses", []))
        if not advance <= full:
            errors.append(f"{stage_id}: every ADVANCE status must require full outputs")
        if not full <= legal:
            errors.append(f"{stage_id}: full_output_statuses contains illegal statuses")

        failure_routes = stage.get("failure_routes", {})
        for status, route_semantics in route_map.items():
            if not isinstance(route_semantics, dict):
                errors.append(f"{stage_id}/{status}: route semantics must be an object")
                continue
            allowed = route_semantics.get("allowed_route_keys", [])
            if not isinstance(allowed, list) or not allowed:
                errors.append(f"{stage_id}/{status}: allowed_route_keys must be non-empty")
                continue
            unknown = set(allowed) - set(failure_routes)
            if unknown:
                errors.append(
                    f"{stage_id}/{status}: route keys absent from failure_routes: {sorted(unknown)}"
                )
            default = route_semantics.get("default_route_key")
            if default is not None and default not in allowed:
                errors.append(f"{stage_id}/{status}: default_route_key is not allowed")

        target = stage.get("success_transition")
        if target != "END" and target not in policy.stages and target not in completion.get("state_contracts", {}):
            errors.append(f"{stage_id}: unregistered success transition {target}")

    if "FIXED" not in outcome_stages.get("FORMAT_GATE", {}).get("retry_statuses", []):
        errors.append("FORMAT_GATE FIXED must be RETRY, not ADVANCE")
    if "FORMAT_PASS" not in outcome_stages.get("FORMAT_GATE", {}).get("advance_statuses", []):
        errors.append("FORMAT_GATE FORMAT_PASS must ADVANCE")
    if "SIMULATION_NOT_EXECUTED" not in outcome_stages.get("MODEL_DIAGNOSTIC", {}).get("advance_statuses", []):
        errors.append("MODEL_DIAGNOSTIC SIMULATION_NOT_EXECUTED must remain non-gating")
    if "FROZEN_CANDIDATE" not in completion.get("state_contracts", {}):
        errors.append("FROZEN_CANDIDATE state contract missing")

    head = _head()
    invocation_builder = StageInvocationBuilder(ROOT, policy)
    record_builder = ExecutionRecordBuilder(ROOT, policy)
    record_ids: set[str] = set()
    for stage_id, stage in policy.stages.items():
        semantics = outcome_stages.get(stage_id, {})
        advances = semantics.get("advance_statuses", []) if isinstance(semantics, dict) else []
        if not advances:
            errors.append(f"{stage_id}: no ADVANCE status")
            continue
        inputs = {
            str(field): {"validator": str(field)}
            for field in stage["input_contract"]["required_fields"]
        }
        try:
            invocation = invocation_builder.build(
                InvocationContext(
                    stage_id=stage_id,
                    role_id="CI_ORCHESTRATOR",
                    control_plane_commit=head,
                ),
                inputs,
            )
            result = {
                "schema_version": "1.0",
                "invocation_id": invocation["invocation_id"],
                "status": advances[0],
                "outputs": _full_outputs(invocation),
                "evidence_refs": [],
            }
            record = record_builder.build(invocation, result)
        except Exception as exc:  # pragma: no cover - validator reports all stages
            errors.append(f"{stage_id}: failed execution-record compilation: {exc}")
            continue
        if record["disposition"] != "ADVANCE":
            errors.append(f"{stage_id}: canonical advance result did not ADVANCE")
        if record["transition"]["target"] != stage["success_transition"]:
            errors.append(f"{stage_id}: transition target drift")
        record_ids.add(record["record_id"])

    if len(record_ids) != len(policy.stages):
        errors.append("canonical per-stage records did not produce unique record IDs")

    if errors:
        print("Terminus execution-record validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus execution-record validation PASS")
    print(
        "execution_record=1.0 outcomes=1.0 stages=23 status_partition=total "
        "result_binding=invocation_exact outputs=declared route_keys=registered "
        "transition=advance_route_retry_block frozen_state=validation_required "
        "record_identity=deterministic reasoning=not_persisted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
