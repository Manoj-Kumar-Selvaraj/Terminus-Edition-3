"""External-gate dispatch/await projection for the task controller."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from retrieval.policy import RetrievalPolicy

from .ledger import ExecutionLedger

_EXTERNAL_ROLE_CLASS = "EXTERNAL_GATE"


def is_external_stage(policy: RetrievalPolicy, stage_id: str) -> bool:
    """Return whether a registered stage is executed by an external gate."""
    stage = policy.stages.get(stage_id)
    return isinstance(stage, dict) and stage.get("role_class") == _EXTERNAL_ROLE_CLASS


def validate_external_result(
    policy: RetrievalPolicy,
    invocation: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Fail closed when an external result is not bound to an external run identity."""
    stage = invocation.get("stage")
    if not isinstance(stage, Mapping):
        return
    stage_id = stage.get("stage_id")
    if not isinstance(stage_id, str) or not is_external_stage(policy, stage_id):
        return
    outputs = result.get("outputs")
    if not isinstance(outputs, Mapping):
        raise ValueError("external-gate result outputs must be an object")
    run_id = _run_id(stage_id, outputs)
    if not run_id:
        raise ValueError(
            f"external-gate result for {stage_id} requires a non-empty immutable run ID"
        )
    status = result.get("status")
    if status == "DISPATCHED" and result.get("blocking_reason") is not None:
        raise ValueError("DISPATCHED external-gate result must not carry blocking_reason")


def project_external_state(
    root: Path,
    resolver: Any,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Project generic stage actions into explicit external DISPATCH/AWAIT actions."""
    projected = json.loads(json.dumps(snapshot))
    next_action = projected.get("next")
    if not isinstance(next_action, dict):
        return projected
    stage_id = next_action.get("stage_id")
    if not isinstance(stage_id, str) or not is_external_stage(resolver.policy, stage_id):
        return projected

    action = next_action.get("action")
    if action == "INVOKE_STAGE":
        next_action["action"] = "DISPATCH_EXTERNAL_GATE"
        next_action["external_gate"] = True
        next_action["reason"] = (
            f"external gate {stage_id} has no current completed result; dispatch one bounded external run"
        )
    elif action == "RETRY_STAGE":
        record = _latest_stage_record(root, str(projected["task_id"]), stage_id)
        if record and record.get("status") == "DISPATCHED":
            next_action["action"] = "AWAIT_EXTERNAL_GATE"
            next_action["external_gate"] = True
            run_id = _run_id(stage_id, record.get("outputs", {}))
            if run_id:
                next_action["external_run_id"] = run_id
            next_action["reason"] = (
                f"external gate {stage_id} was dispatched and has no current completion result yet"
            )

    projected.pop("state_snapshot_id", None)
    projected["state_snapshot_id"] = resolver._snapshot_id(projected)
    return resolver._ordered_snapshot(projected)


def _latest_stage_record(root: Path, task_id: str, stage_id: str) -> dict[str, Any] | None:
    ledger = ExecutionLedger(root, task_id)
    events = ledger.load(validate_record_files=True)
    for event in reversed(events):
        if event.get("stage_id") != stage_id:
            continue
        relative = event.get("record_path")
        if not isinstance(relative, str):
            return None
        path = (root / relative).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    return None


def _run_id(stage_id: str, outputs: Mapping[str, Any]) -> str | None:
    values: list[Any]
    if stage_id == "HARBOR_LLMAJ":
        values = [outputs.get("HARBOR_RUN_ID"), outputs.get("EXTERNAL_RUN_ID")]
    else:
        values = [outputs.get("EXTERNAL_RUN_ID")]
    for value in values:
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    return None
