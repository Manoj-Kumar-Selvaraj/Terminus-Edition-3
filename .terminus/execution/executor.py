"""Executor-neutral primitives for Terminus stage execution.

Executors consume an already-authorized stage invocation and may return a raw
StageResult. They never write execution records, ledgers, or workflow state.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Mapping

from .invocation import StageInvocationBuilder


class ExecutorMode(str, Enum):
    """Supported executor surfaces."""

    MANUAL_CHAT = "MANUAL_CHAT"
    LOCAL_COMMAND = "LOCAL_COMMAND"


FORBIDDEN_REASONING_FIELDS = frozenset(
    {
        "chain_of_thought",
        "reasoning",
        "reasoning_chain",
        "scratchpad",
        "private_reasoning",
        "hidden_reasoning",
    }
)


def canonical_json(value: Any) -> str:
    """Return deterministic JSON used for executor identities and transport."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def nested_keys(value: Any) -> set[str]:
    """Collect lowercase mapping keys recursively for hidden-field checks."""

    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.add(str(key).lower())
            found.update(nested_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(nested_keys(item))
    return found


def validate_executable_invocation(invocation: Mapping[str, Any]) -> None:
    """Perform transport checks after canonical authorization has succeeded."""

    if invocation.get("schema_version") != "1.0":
        raise ValueError("executor requires stage invocation schema_version 1.0")
    if invocation.get("readiness") != "READY":
        raise ValueError("executor requires a READY stage invocation")
    invocation_id = invocation.get("invocation_id")
    if not isinstance(invocation_id, str) or not invocation_id.startswith("inv_"):
        raise ValueError("executor invocation_id is missing or invalid")

    stage = invocation.get("stage")
    if not isinstance(stage, Mapping):
        raise ValueError("executor invocation stage projection is invalid")
    for field in ("stage_id", "role_id"):
        if not isinstance(stage.get(field), str) or not stage.get(field):
            raise ValueError(f"executor invocation requires stage.{field}")

    identity = dict(invocation)
    identity.pop("invocation_id", None)
    expected = StageInvocationBuilder._invocation_id(identity)
    if invocation_id != expected:
        raise ValueError("executor invocation_id does not match invocation content")

    forbidden = nested_keys(invocation) & FORBIDDEN_REASONING_FIELDS
    if forbidden:
        raise ValueError(
            "executor invocation contains forbidden private-reasoning fields: "
            + ", ".join(sorted(forbidden))
        )


def validate_stage_result_shape(
    result: Mapping[str, Any],
    *,
    invocation_id: str,
    handoff_id: str,
) -> None:
    """Perform transport checks only; semantic acceptance is recorder-owned."""

    required = {
        "schema_version",
        "handoff_id",
        "invocation_id",
        "output_task_commit",
        "status",
        "outputs",
        "evidence_refs",
    }
    allowed = required | {"route_key", "blocking_reason"}
    missing = required - set(result)
    extra = set(result) - allowed
    if missing:
        raise ValueError(f"executor result missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"executor result contains undeclared fields: {sorted(extra)}")
    if result.get("schema_version") != "1.0":
        raise ValueError("executor result schema_version must be 1.0")
    if result.get("handoff_id") != handoff_id:
        raise ValueError("executor result handoff_id does not match exact handoff")
    if result.get("invocation_id") != invocation_id:
        raise ValueError("executor result invocation_id does not match handoff")
    if not isinstance(result.get("output_task_commit"), str) or not result.get(
        "output_task_commit"
    ):
        raise ValueError("executor result requires output_task_commit")
    if not isinstance(result.get("status"), str) or not result.get("status"):
        raise ValueError("executor result requires non-empty status")
    if not isinstance(result.get("outputs"), Mapping):
        raise ValueError("executor result outputs must be an object")
    if not isinstance(result.get("evidence_refs"), list):
        raise ValueError("executor result evidence_refs must be an array")

    forbidden = nested_keys(result) & FORBIDDEN_REASONING_FIELDS
    if forbidden:
        raise ValueError(
            "executor result contains forbidden private-reasoning fields: "
            + ", ".join(sorted(forbidden))
        )
