"""Resolve canonical quality execution modes for controller routing."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

_POLICY_PATH = ".terminus/agents/quality_execution_mode.json"
_Q46_ENV = "TERMINUS_Q4_Q6_MODE"
_Q8_ENV = "TERMINUS_Q8_MODE"


class QualityExecutionModeError(ValueError):
    """Raised when the quality execution-mode policy is invalid."""


def _load(root: Path) -> dict[str, Any]:
    path = root / _POLICY_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityExecutionModeError(f"cannot load {_POLICY_PATH}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualityExecutionModeError(f"{_POLICY_PATH} must contain one object")
    return value


def _resolve_one(
    *,
    name: str,
    configured: Any,
    allowed: Any,
    override: str | None,
) -> str:
    allowed_values = (
        {str(value).upper() for value in allowed if isinstance(value, str)}
        if isinstance(allowed, list)
        else set()
    )
    if not allowed_values:
        raise QualityExecutionModeError(f"{name} has no allowed values")
    raw = override if override is not None else os.environ.get(name)
    if raw is None or not str(raw).strip():
        raw = configured
    mode = str(raw).strip().upper()
    if mode not in allowed_values:
        raise QualityExecutionModeError(
            f"invalid {name}={mode!r}; allowed={sorted(allowed_values)}"
        )
    return mode


def _validate_inline_sequences(value: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        raise QualityExecutionModeError("inline_stage_sequences must be an object")
    sequences: dict[str, list[dict[str, Any]]] = {}
    for stage_id, raw_steps in value.items():
        if not isinstance(stage_id, str) or not stage_id:
            raise QualityExecutionModeError("inline stage sequence has invalid stage id")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise QualityExecutionModeError(f"inline stage sequence is empty: {stage_id}")
        steps: list[dict[str, Any]] = []
        seen_fields: set[str] = set()
        for raw in raw_steps:
            if not isinstance(raw, dict):
                raise QualityExecutionModeError(f"invalid inline step for {stage_id}")
            role_id = str(raw.get("role_id") or "")
            result_field = str(raw.get("result_field") or "")
            satisfied = raw.get("satisfied_values")
            if not role_id or not result_field or not isinstance(satisfied, list) or not satisfied:
                raise QualityExecutionModeError(f"incomplete inline step for {stage_id}")
            if result_field in seen_fields:
                raise QualityExecutionModeError(
                    f"duplicate inline result field for {stage_id}: {result_field}"
                )
            seen_fields.add(result_field)
            steps.append(
                {
                    "role_id": role_id,
                    "result_field": result_field,
                    "satisfied_values": [str(item) for item in satisfied],
                }
            )
        sequences[stage_id] = steps
    return sequences


def resolve_quality_execution_modes(
    root: Path,
    *,
    q4_q6_override: str | None = None,
    q8_override: str | None = None,
) -> dict[str, Any]:
    """Return validated quality modes and same-chat role policy.

    CLI overrides win over environment variables, which win over the versioned
    defaults in ``quality_execution_mode.json``.
    """
    root = root.resolve()
    policy = _load(root)
    variables = policy.get("variables")
    allowed = policy.get("allowed_values")
    inline = policy.get("inline_same_chat")
    checkpoints = policy.get("mandatory_same_chat_checkpoints")
    independent = policy.get("independent_quality")
    if not all(
        isinstance(value, dict)
        for value in (variables, allowed, inline, checkpoints, independent)
    ):
        raise QualityExecutionModeError("quality execution-mode policy structure is invalid")

    policy_document = str(policy.get("policy_document") or "")
    if not policy_document or not (root / policy_document).is_file():
        raise QualityExecutionModeError("quality execution-mode policy document is missing")

    q4_q6_mode = _resolve_one(
        name=_Q46_ENV,
        configured=variables.get(_Q46_ENV),
        allowed=allowed.get(_Q46_ENV),
        override=q4_q6_override,
    )
    q8_mode = _resolve_one(
        name=_Q8_ENV,
        configured=variables.get(_Q8_ENV),
        allowed=allowed.get(_Q8_ENV),
        override=q8_override,
    )

    producer_classes = {
        str(value)
        for value in inline.get("producer_role_classes", [])
        if isinstance(value, str)
    }
    creation_governor_role_ids = {
        str(value)
        for value in inline.get("creation_governor_role_ids", [])
        if isinstance(value, str)
    }
    quality_role_ids = {
        str(value)
        for value in inline.get("quality_role_ids", [])
        if isinstance(value, str)
    }
    inline_sequences = _validate_inline_sequences(policy.get("inline_stage_sequences"))
    mandatory_roles = [
        str(value)
        for value in independent.get("mandatory_role_keys", [])
        if isinstance(value, str)
    ]
    optional_roles = [
        str(value)
        for value in independent.get("optional_role_keys", [])
        if isinstance(value, str)
    ]
    if not producer_classes or not quality_role_ids:
        raise QualityExecutionModeError("same-chat role policy is incomplete")
    if creation_governor_role_ids != {"A10_COMPLEXITY_GOVERNOR"}:
        raise QualityExecutionModeError(
            "same-chat creation governor must be A10_COMPLEXITY_GOVERNOR"
        )
    if set(checkpoints) != {"Q1", "Q2", "Q3", "Q5", "Q7"}:
        raise QualityExecutionModeError("mandatory same-chat Q checkpoint set drift")
    spec_sequence = inline_sequences.get("SPEC_ALIGNMENT")
    if spec_sequence is None or [step["role_id"] for step in spec_sequence] != [
        "Q1_SPEC_GAP_REPAIRER",
        "Q2_VERIFIER_COVERAGE_REPAIRER",
        "Q3_SPEC_AMBIGUITY_REPAIRER",
    ]:
        raise QualityExecutionModeError("SPEC_ALIGNMENT must execute Q1, Q2 and Q3 in order")
    if [step["result_field"] for step in spec_sequence] != [
        "Q1_STATUS",
        "Q2_STATUS",
        "Q3_STATUS",
    ]:
        raise QualityExecutionModeError("SPEC_ALIGNMENT inline result-field binding drift")
    if not {step["role_id"] for step in spec_sequence} <= quality_role_ids:
        raise QualityExecutionModeError("SPEC_ALIGNMENT sequence contains non-inline Q role")
    if mandatory_roles != ["spec-test-contract", "production-logic"]:
        raise QualityExecutionModeError("mandatory independent quality roles must be Q4 then Q6")
    if optional_roles != ["difficulty-sim-gpt", "difficulty-sim-claude"]:
        raise QualityExecutionModeError("optional independent diagnostics must be Q8 GPT then Claude")

    return {
        "policy_version": str(policy.get("policy_version") or ""),
        "policy_document": policy_document,
        "q4_q6_mode": q4_q6_mode,
        "q8_mode": q8_mode,
        "producer_role_classes": sorted(producer_classes),
        "inline_creation_governor_role_ids": sorted(creation_governor_role_ids),
        "inline_quality_role_ids": sorted(quality_role_ids),
        "inline_stage_sequences": deepcopy(inline_sequences),
        "mandatory_same_chat_checkpoints": dict(sorted(checkpoints.items())),
        "mandatory_quality_role_keys": mandatory_roles,
        "optional_q8_role_keys": optional_roles,
        "source": _POLICY_PATH,
    }


def inline_execution_mode(
    policy: dict[str, Any],
    *,
    role_class: str,
    role_id: str,
) -> str:
    """Return the default ChatGPT execution mode for a non-quality stage."""
    if role_id in set(policy["inline_creation_governor_role_ids"]):
        return "INLINE_SPECIALIST"
    if role_id in set(policy["inline_quality_role_ids"]):
        return "INLINE_SPECIALIST"
    if role_class in set(policy["producer_role_classes"]):
        return "INLINE_SPECIALIST"
    if role_class == "CONTROLLER":
        return "ORCHESTRATOR_DIRECT"
    return "FRESH_ROLE_CHAT"
