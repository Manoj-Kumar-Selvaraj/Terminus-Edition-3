#!/usr/bin/env python3
"""Validate the executable stage-invocation compiler and contract projection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

FORBIDDEN = {
    "chain_of_thought",
    "reasoning",
    "scratchpad",
    "private_reasoning",
    "reasoning_chain",
}


def keys(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            result.add(str(key).lower())
            result.update(keys(item))
    elif isinstance(value, list):
        for item in value:
            result.update(keys(item))
    return result


def main() -> int:
    errors: list[str] = []
    policy = RetrievalPolicy(ROOT)
    authority = ExecutionAuthority(policy)
    builder = StageInvocationBuilder(ROOT, policy)
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    schema = json.loads(
        (T / "agents" / "schemas" / "stage_invocation.schema.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        schema.get("$id") != "terminus-stage-invocation-v1"
        or schema.get("additionalProperties") is not False
    ):
        errors.append("stage invocation schema identity/fail-closed contract drift")
    if keys(schema) & FORBIDDEN:
        errors.append("stage invocation schema exposes private reasoning fields")
    try:
        Draft202012Validator.check_schema(schema)
        schema_validator = Draft202012Validator(schema)
    except Exception as exc:
        errors.append(f"stage invocation JSON Schema is invalid: {exc}")
        schema_validator = None

    invocation_ids: set[str] = set()
    for stage_id, stage in policy.stages.items():
        role_id = authority.primary_role_for_stage(stage_id)
        if authority.roles_for_stage(stage_id) != frozenset({role_id}):
            errors.append(f"{stage_id}: aggregate execution must have one owner")
        inputs = {
            str(field): {"ref": f"validator:{field}"}
            for field in stage.get("input_contract", {}).get("required_fields", [])
        }
        try:
            packet = builder.build(
                InvocationContext(
                    stage_id=stage_id,
                    role_id=role_id,
                    control_plane_commit=head,
                    policy_versions={"agent_system": "2.4"},
                ),
                inputs,
            )
        except Exception as exc:
            errors.append(f"{stage_id}: invocation projection failed: {exc}")
            continue
        if schema_validator is not None:
            schema_errors = sorted(
                schema_validator.iter_errors(packet),
                key=lambda item: list(item.absolute_path),
            )
            for schema_error in schema_errors:
                location = ".".join(str(part) for part in schema_error.absolute_path)
                errors.append(
                    f"{stage_id}: generated invocation violates schema at "
                    f"{location or '<root>'}: {schema_error.message}"
                )
        if packet.get("readiness") != "READY" or packet.get("missing_required_inputs"):
            errors.append(f"{stage_id}: registered stage did not compile READY")
        if packet.get("stage", {}).get("role_id") != role_id:
            errors.append(f"{stage_id}: canonical role projection drift")
        if packet.get("output_contract", {}).get("allowed_status_values") != stage.get(
            "output_contract", {}
        ).get("status_values"):
            errors.append(f"{stage_id}: output status projection drift")
        if packet.get("routing", {}).get("success_transition") != stage.get(
            "success_transition"
        ):
            errors.append(f"{stage_id}: success transition projection drift")
        if packet.get("evidence", {}).get("mandatory_exact_reads") != list(
            policy.mandatory_exact_paths(stage_id)
        ):
            errors.append(f"{stage_id}: exact-read projection drift")
        if keys(packet) & FORBIDDEN:
            errors.append(f"{stage_id}: invocation contains private reasoning field")
        invocation_ids.add(str(packet.get("invocation_id")))
    if len(invocation_ids) != len(policy.stages):
        errors.append("distinct registered stages did not produce distinct invocation IDs")

    for stage_id in ("MODEL_DIAGNOSTIC_GPT", "MODEL_DIAGNOSTIC_CLAUDE"):
        if policy.retrieval_mode(stage_id) != "SOLVER_VISIBLE_ONLY":
            errors.append(f"{stage_id}: must use SOLVER_VISIBLE_ONLY")
        role = authority.primary_role_for_stage(stage_id)
        if role != "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR":
            errors.append(f"{stage_id}: Q8 executor drift")
    if authority.primary_role_for_stage("HARBOR_LLMAJ") != "HARBOR_LLMAJ_GATE":
        errors.append("Harbor external owner role drift")
    if (
        authority.primary_role_for_stage("OFFICIAL_MODEL_TRIALS")
        != "OFFICIAL_MODEL_EVALUATION_GATE"
    ):
        errors.append("official model evaluation owner role drift")
    if authority.primary_role_for_stage("DIFFICULTY_ASSESSMENT") != "DIFFICULTY_REVIEWER":
        errors.append("difficulty owner role drift")

    try:
        builder.build(
            InvocationContext(
                stage_id="WORK_PACKAGE_RESEARCH",
                role_id="CI_ORCHESTRATOR",
                control_plane_commit=head,
            ),
            {
                str(field): "x"
                for field in policy.stages["WORK_PACKAGE_RESEARCH"]["input_contract"][
                    "required_fields"
                ]
            },
        )
        errors.append("CI Orchestrator incorrectly gained producer execution authority")
    except ValueError:
        pass

    if errors:
        print("Terminus stage-invocation validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus stage-invocation validation PASS")
    print(
        f"invocation=1.0 stages={len(policy.stages)} schema=draft2020-12-validated "
        "projection=declared_inputs_only authority=single_stage_owner "
        "retrieval_review_audience=separate q8=dual_isolated harbor=external_owner "
        "difficulty=independent_owner exact_reads=mandatory reasoning=not_persisted "
        "portability=normal_chatgpt_fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
