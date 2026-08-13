#!/usr/bin/env python3
"""Validate the executable stage-invocation compiler and contract projection."""

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
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

REQUIRED = [
    T / "agents" / "STAGE_INVOCATION.md",
    T / "agents" / "schemas" / "stage_invocation.schema.json",
    T / "execution" / "__init__.py",
    T / "execution" / "authority.py",
    T / "execution" / "invocation.py",
    T / "execution" / "cli.py",
    T / "tests" / "test_stage_invocation.py",
]

POLICY_MARKERS = [
    "Stage-invocation policy version: `1.0`",
    "Input projection",
    "Mandatory exact reads",
    "Retrieval projection",
    "Output contract projection",
    "Deterministic identity",
    "No hidden reasoning",
    "Normal ChatGPT",
]

CODE_MARKERS = [
    "BLOCKED_MISSING_INPUTS",
    "ignored_input_count",
    "mandatory_exact_reads",
    "authorized_evidence_classes",
    "SKIPPED_BLOCKED_INPUTS",
    "DIRECT_READ_FALLBACK",
    "allowed_status_values",
    "success_transition",
    "_require_loaded_contract_snapshot",
    "_validate_policy_versions",
    "item.pop(\"score\", None)",
    "_invocation_id",
    "execution_authority.validate_context",
]

CLI_MARKERS = [
    "--control-plane-commit",
    "--task-commit",
    "--inputs-json",
    "--input",
    "--query",
    "--output",
]

FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "reasoning",
    "scratchpad",
    "private_reasoning",
}


def _all_keys(value: Any) -> set[str]:
    output: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            output.add(str(key).lower())
            output.update(_all_keys(item))
    elif isinstance(value, list):
        for item in value:
            output.update(_all_keys(item))
    return output


def _require_markers(errors: list[str], text: str, label: str, markers: list[str]) -> None:
    lower = text.lower()
    for marker in markers:
        if marker.lower() not in lower:
            errors.append(f"{label} missing marker: {marker}")


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    policy_text = (T / "agents" / "STAGE_INVOCATION.md").read_text(encoding="utf-8")
    _require_markers(errors, policy_text, "STAGE_INVOCATION.md", POLICY_MARKERS)

    code_text = (T / "execution" / "invocation.py").read_text(encoding="utf-8")
    _require_markers(errors, code_text, "invocation.py", CODE_MARKERS)
    cli_text = (T / "execution" / "cli.py").read_text(encoding="utf-8")
    _require_markers(errors, cli_text, "execution/cli.py", CLI_MARKERS)

    schema = json.loads(
        (T / "agents" / "schemas" / "stage_invocation.schema.json").read_text(
            encoding="utf-8"
        )
    )
    if schema.get("$id") != "terminus-stage-invocation-v1":
        errors.append("stage invocation schema has wrong $id")
    if schema.get("additionalProperties") is not False:
        errors.append("stage invocation schema must fail closed on top-level properties")
    schema_keys = _all_keys(schema)
    forbidden_schema = schema_keys & FORBIDDEN_REASONING_KEYS
    if forbidden_schema:
        errors.append(
            f"stage invocation schema exposes private reasoning fields: {sorted(forbidden_schema)}"
        )
    authority_schema = schema.get("properties", {}).get("authority", {})
    dependent = authority_schema.get("dependentRequired", {})
    if dependent.get("task_id") != ["task_commit"]:
        errors.append("schema must bind task_id to task_commit")
    if dependent.get("task_commit") != ["task_id"]:
        errors.append("schema must bind task_commit to task_id")
    retrieval_items = (
        schema.get("properties", {})
        .get("retrieval", {})
        .get("properties", {})
        .get("retrieved_context", {})
        .get("items", {})
    )
    if retrieval_items.get("additionalProperties") is not False:
        errors.append("retrieved_context items must be fail-closed objects")

    policy = RetrievalPolicy(ROOT)
    execution_authority = ExecutionAuthority(policy)
    builder = StageInvocationBuilder(ROOT, policy)
    control_commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(policy.stages) != 23:
        errors.append(f"expected 23 stages, found {len(policy.stages)}")

    invocation_ids: set[str] = set()
    for stage_id, stage in policy.stages.items():
        required_fields = stage.get("input_contract", {}).get("required_fields", [])
        inputs = {
            str(field): {"ref": f"validator:{field}"} for field in required_fields
        }
        role_id = execution_authority.primary_role_for_stage(stage_id)
        try:
            packet = builder.build(
                InvocationContext(
                    stage_id=stage_id,
                    role_id=role_id,
                    control_plane_commit=control_commit,
                    policy_versions={"agent_system": "2.4"},
                ),
                inputs,
            )
        except Exception as exc:  # pragma: no cover - validator must report all stages
            errors.append(f"stage {stage_id} failed invocation projection: {exc}")
            continue
        if packet["readiness"] != "READY":
            errors.append(f"stage {stage_id} did not compile READY")
        if packet["missing_required_inputs"]:
            errors.append(f"stage {stage_id} reports unexpected missing inputs")
        if packet["stage"]["role_id"] != role_id:
            errors.append(f"stage {stage_id} execution role drift")
        if (
            packet["output_contract"]["allowed_status_values"]
            != stage["output_contract"]["status_values"]
        ):
            errors.append(f"stage {stage_id} status vocabulary drift")
        if packet["routing"]["success_transition"] != stage["success_transition"]:
            errors.append(f"stage {stage_id} success transition drift")
        if packet["evidence"]["mandatory_exact_reads"] != list(
            policy.mandatory_exact_paths(stage_id)
        ):
            errors.append(f"stage {stage_id} exact-read projection drift")
        if _all_keys(packet) & FORBIDDEN_REASONING_KEYS:
            errors.append(f"stage {stage_id} packet contains private reasoning field")
        invocation_ids.add(packet["invocation_id"])

    if len(invocation_ids) != len(policy.stages):
        errors.append("distinct stage projections did not produce distinct invocation IDs")

    if "CI_ORCHESTRATOR" not in policy.allowed_roles_for_stage("WORK_PACKAGE_RESEARCH"):
        errors.append("CI Orchestrator must retain retrieval/routing visibility for creation stages")
    if "CI_ORCHESTRATOR" in execution_authority.roles_for_stage("WORK_PACKAGE_RESEARCH"):
        errors.append("CI Orchestrator retrieval visibility must not grant A1 execution authority")
    if "CREATION_CONTROLLER" in execution_authority.roles_for_stage("WORK_PACKAGE_RESEARCH"):
        errors.append("Creation Controller routing visibility must not grant A1 execution authority")

    blocked = builder.build(
        InvocationContext(
            stage_id="RULE_RESOLUTION",
            role_id="CREATION_CONTROLLER",
            control_plane_commit=control_commit,
        ),
        {},
        retrieval_query="authority",
    )
    if blocked["readiness"] != "BLOCKED_MISSING_INPUTS":
        errors.append("missing required input did not block invocation")
    if blocked["retrieval"]["status"] != "SKIPPED_BLOCKED_INPUTS":
        errors.append("blocked invocation must not run retrieval")
    if blocked["missing_required_inputs"] != ["CREATION_REQUEST"]:
        errors.append("RULE_RESOLUTION missing-input projection drift")

    projected = builder.build(
        InvocationContext(
            stage_id="RULE_RESOLUTION",
            role_id="CREATION_CONTROLLER",
            control_plane_commit=control_commit,
        ),
        {"CREATION_REQUEST": "create", "UNDECLARED_SECRET": "drop"},
    )
    if projected["ignored_input_count"] != 1:
        errors.append("undeclared input count drift")
    if "UNDECLARED_SECRET" in json.dumps(projected, sort_keys=True):
        errors.append("undeclared input name leaked into invocation packet")

    try:
        builder.build(
            InvocationContext(
                stage_id="WORK_PACKAGE_RESEARCH",
                role_id="CI_ORCHESTRATOR",
                control_plane_commit=control_commit,
            ),
            {
                str(field): {"ref": f"validator:{field}"}
                for field in policy.stages["WORK_PACKAGE_RESEARCH"]["input_contract"][
                    "required_fields"
                ]
            },
        )
        errors.append("controller observer was incorrectly accepted as A1 executor")
    except ValueError as exc:
        if "execution role CI_ORCHESTRATOR is not authorized" not in str(exc):
            errors.append(f"controller observer rejection used unexpected error: {exc}")

    if errors:
        print("Terminus stage-invocation validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus stage-invocation validation PASS")
    print(
        "invocation=1.0 stages=23 projection=declared_inputs_only "
        "authority=executable_role_task_control_snapshot retrieval_audience=separate "
        "exact_reads=mandatory retrieval=optional missing_inputs=blocked "
        "ignored_names=not_leaked identity=score_independent reasoning=not_persisted "
        "portability=normal_chatgpt_fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
