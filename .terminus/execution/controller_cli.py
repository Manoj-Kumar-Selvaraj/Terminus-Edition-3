#!/usr/bin/env python3
"""Task-scoped Terminus controller helpers: record, status, next, materialize, continue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.executor import ExecutorMode
    from execution.external_gate import project_external_state, validate_external_result
    from execution.invocation import StageInvocationBuilder
    from execution.ledger import ExecutionLedger
    from execution.record import ExecutionRecordBuilder
    from execution.runner import ExecutorRunner
    from execution.state import WorkflowStateResolver
    from remediation.router import RemediationInterlock
    from retrieval.models import InvocationContext
else:
    from .executor import ExecutorMode
    from .external_gate import project_external_state, validate_external_result
    from .invocation import StageInvocationBuilder
    from .ledger import ExecutionLedger
    from .record import ExecutionRecordBuilder
    from .runner import ExecutorRunner
    from .state import WorkflowStateResolver
    from remediation.router import RemediationInterlock
    from retrieval.models import InvocationContext

QUALITY_LIFECYCLE_WORKFLOW = ".github/workflows/terminus-quality-lifecycle.yml"
QUALITY_LIFECYCLE_STAGES = {
    "QUALITY_INTERLOCK": ("spec-test-contract", "production-logic"),
    "MODEL_DIAGNOSTIC_GPT": ("difficulty-sim-gpt",),
    "MODEL_DIAGNOSTIC_CLAUDE": ("difficulty-sim-claude",),
}
CONTROLLER_STAGE_WORKFLOW = ".github/workflows/terminus-controller-stage.yml"
AUTOMATED_CONTROLLER_STAGES = {"RULE_RESOLUTION"}


def _json_object(path: str | None, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def _write_or_print(value: Any, output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def _state_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--control-plane-commit", required=True)
    parser.add_argument("--freshness-json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="derive the complete workflow snapshot")
    _state_args(status)
    status.add_argument("--output")

    next_parser = sub.add_parser("next", help="return only the deterministic next action")
    _state_args(next_parser)
    next_parser.add_argument("--output")

    materialize = sub.add_parser(
        "materialize", help="derive and persist .terminus/workflows/<task>/state.json"
    )
    _state_args(materialize)
    materialize.add_argument("--output")

    record = sub.add_parser(
        "record", help="validate a result, persist immutable record+ledger, materialize state"
    )
    record.add_argument("--invocation", required=True)
    record.add_argument("--result", required=True)
    record.add_argument("--freshness-json")
    record.add_argument("--no-materialize", action="store_true")
    record.add_argument("--output")

    continue_parser = sub.add_parser(
        "continue", help="derive next action and compile the next owner invocation when applicable"
    )
    _state_args(continue_parser)
    continue_parser.add_argument("--inputs-json")
    continue_parser.add_argument("--query")
    continue_parser.add_argument("--db")
    continue_parser.add_argument("--retrieval-limit", type=int, default=10)
    continue_parser.add_argument("--max-chars", type=int, default=30000)
    continue_parser.add_argument(
        "--prepare-executor",
        choices=[mode.value for mode in ExecutorMode],
        help="also prepare a non-mutating executor handoff for ordinary invoke/retry/remediation actions",
    )
    continue_parser.add_argument("--output")
    return parser


def _remediation_view(
    root: Path,
    snapshot: dict[str, Any],
    *,
    task_id: str,
    task_commit: str,
) -> dict[str, Any]:
    override = RemediationInterlock(root).next_override(
        task_id=task_id,
        task_commit=task_commit,
    )
    if override is None:
        return snapshot
    projected = dict(snapshot)
    projected["next"] = override
    return projected


def _resolve_state(
    root: Path, args: argparse.Namespace
) -> tuple[WorkflowStateResolver, dict[str, Any], dict[str, Any]]:
    resolver = WorkflowStateResolver(root)
    freshness = (
        _json_object(args.freshness_json, "--freshness-json")
        if args.freshness_json
        else None
    )
    durable_snapshot = resolver.resolve(
        task_id=args.task_id,
        task_commit=args.task_commit,
        control_plane_commit=args.control_plane_commit,
        freshness_overlay=freshness,
    )
    durable_snapshot = project_external_state(root, resolver, durable_snapshot)
    controller_view = _remediation_view(
        root,
        durable_snapshot,
        task_id=args.task_id,
        task_commit=args.task_commit,
    )
    return resolver, durable_snapshot, controller_view


def _quality_lifecycle_dispatch(args: argparse.Namespace, stage_id: str) -> dict[str, Any]:
    roles = QUALITY_LIFECYCLE_STAGES[stage_id]
    budgets = {
        "QUALITY_INTERLOCK": {"Q4": 3, "Q6": 2},
        "MODEL_DIAGNOSTIC_GPT": {"Q8_GPT": 1},
        "MODEL_DIAGNOSTIC_CLAUDE": {"Q8_CLAUDE": 1},
    }[stage_id]
    return {
        "status": "READY_TO_DISPATCH",
        "stage_id": stage_id,
        "quality_lifecycle": True,
        "workflow": QUALITY_LIFECYCLE_WORKFLOW,
        "inputs": {
            "task": args.task_id,
            "stage": stage_id,
            "publish_results": True,
        },
        "quality_role_keys": list(roles),
        "budget_limits": budgets,
        "backend_selection": "repository Q_*_ENABLED variables; exactly one backend",
        "credential_policy": "existing selected secret only; login/refresh/fallback forbidden",
    }


def _controller_stage_dispatch(
    args: argparse.Namespace,
    packet: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    invocation_id = str(packet["invocation_id"])
    suffix = invocation_id.removeprefix("inv_")[:16]
    branch = f"terminus-controller-request/{args.task_id}/{suffix}"
    request_path = f".terminus/controller-requests/{args.task_id}-{suffix}.json"
    return {
        "status": "READY_TO_DISPATCH",
        "stage_id": packet["stage"]["stage_id"],
        "controller_stage": True,
        "model_backed": False,
        "workflow": CONTROLLER_STAGE_WORKFLOW,
        "trigger": "REQUEST_BRANCH_PUSH",
        "branch": branch,
        "request_path": request_path,
        "request": {
            "schema_version": "1.0",
            "task_id": args.task_id,
            "task_commit": args.task_commit,
            "stage_id": packet["stage"]["stage_id"],
            "expected_main_sha": args.control_plane_commit,
            "inputs": inputs,
        },
        "persistence": "workflow validates, records, replays and fast-forwards main only if main is unchanged",
    }


def _continue_payload(
    root: Path,
    args: argparse.Namespace,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    next_action = snapshot["next"]
    payload: dict[str, Any] = {
        "state_snapshot_id": snapshot["state_snapshot_id"],
        "next": next_action,
    }
    if next_action["action"] == "AWAIT_EXTERNAL_GATE":
        payload["invocation"] = None
        payload["executor_handoff"] = None
        payload["dispatch"] = {
            "status": "AWAITING_EXTERNAL_RESULT",
            "stage_id": next_action["stage_id"],
            "external_run_id": next_action.get("external_run_id"),
        }
        return payload
    if next_action["action"] not in {
        "INVOKE_STAGE",
        "RETRY_STAGE",
        "REMEDIATE_STAGE",
        "DISPATCH_EXTERNAL_GATE",
    }:
        payload["invocation"] = None
        payload["executor_handoff"] = None
        return payload

    stage_id = str(next_action["stage_id"])
    if (
        stage_id in QUALITY_LIFECYCLE_STAGES
        and next_action["action"] in {"INVOKE_STAGE", "RETRY_STAGE"}
    ):
        payload["invocation"] = None
        payload["executor_handoff"] = None
        payload["dispatch"] = _quality_lifecycle_dispatch(args, stage_id)
        return payload

    role_id = str(next_action["primary_role_id"])
    inputs = _json_object(args.inputs_json, "--inputs-json")
    context = InvocationContext(
        stage_id=stage_id,
        role_id=role_id,
        task_id=args.task_id,
        task_commit=args.task_commit,
        control_plane_commit=args.control_plane_commit,
    )
    packet = StageInvocationBuilder(root).build(
        context,
        inputs,
        retrieval_query=args.query,
        retrieval_db=Path(args.db).resolve() if args.db else None,
        retrieval_limit=args.retrieval_limit,
        max_chars=args.max_chars,
    )
    payload["invocation"] = packet
    payload["executor_handoff"] = None
    if next_action["action"] == "DISPATCH_EXTERNAL_GATE":
        payload["dispatch"] = {
            "status": "READY_TO_DISPATCH" if packet.get("readiness") == "READY" else "BLOCKED",
            "stage_id": stage_id,
            "external_gate": True,
        }
        return payload

    if (
        stage_id in AUTOMATED_CONTROLLER_STAGES
        and next_action["action"] in {"INVOKE_STAGE", "RETRY_STAGE"}
        and packet.get("readiness") == "READY"
    ):
        if packet.get("stage", {}).get("role_class") != "CONTROLLER":
            raise ValueError("automated controller stage must have CONTROLLER role_class")
        if packet.get("output_contract", {}).get("semantic_reviewers"):
            raise ValueError("automated controller stage cannot replace semantic reviewers")
        payload["dispatch"] = _controller_stage_dispatch(args, packet, inputs)
        return payload

    executor_mode = getattr(args, "prepare_executor", None)
    if executor_mode and packet.get("readiness") == "READY":
        prepared = ExecutorRunner(root).prepare(
            packet,
            executor_mode=executor_mode,
        )
        payload["executor_handoff"] = prepared["handoff"]
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()

    if args.command in {"status", "next", "materialize", "continue"}:
        resolver, durable_snapshot, controller_view = _resolve_state(root, args)
        if args.command == "status":
            _write_or_print(controller_view, args.output)
            return 0
        if args.command == "next":
            _write_or_print(controller_view["next"], args.output)
            return 0 if controller_view["next"]["action"] == "END" else 2
        if args.command == "materialize":
            path = resolver.materialize(durable_snapshot)
            result = {"path": str(path.relative_to(root)), "state": controller_view}
            _write_or_print(result, args.output)
            return 0
        payload = _continue_payload(root, args, controller_view)
        _write_or_print(payload, args.output)
        invocation = payload.get("invocation")
        if isinstance(invocation, dict):
            return 0 if invocation.get("readiness") == "READY" else 2
        dispatch = payload.get("dispatch")
        if isinstance(dispatch, dict):
            return 0 if dispatch.get("status") == "READY_TO_DISPATCH" else 2
        return 0 if controller_view["next"]["action"] == "END" else 2

    invocation = _json_object(args.invocation, "--invocation")
    result = _json_object(args.result, "--result")
    builder = ExecutionRecordBuilder(root)
    validate_external_result(builder.policy, invocation, result)
    record = builder.build(invocation, result)
    authority = record.get("authority")
    if not isinstance(authority, dict):
        raise ValueError("execution record authority is invalid")
    task_id = authority.get("task_id")
    control_commit = authority.get("control_plane_commit")
    lineage = record.get("task_lineage")
    output_task_commit = (
        lineage.get("output_task_commit") if isinstance(lineage, dict) else None
    )
    if not all(
        isinstance(value, str) and value
        for value in (task_id, output_task_commit, control_commit)
    ):
        raise ValueError(
            "record persistence requires task_id, output_task_commit and control_plane_commit"
        )

    ledger = ExecutionLedger(root, task_id)
    event = ledger.append(record)
    remediation_updates = RemediationInterlock(root).on_record(task_id=task_id)
    response: dict[str, Any] = {
        "record": record,
        "ledger_event": event,
        "remediation_updates": remediation_updates,
    }
    if not args.no_materialize:
        freshness = (
            _json_object(args.freshness_json, "--freshness-json")
            if args.freshness_json
            else None
        )
        resolver = WorkflowStateResolver(root)
        durable_snapshot = resolver.resolve(
            task_id=task_id,
            task_commit=output_task_commit,
            control_plane_commit=control_commit,
            freshness_overlay=freshness,
        )
        durable_snapshot = project_external_state(root, resolver, durable_snapshot)
        resolver.materialize(durable_snapshot)
        response["state"] = _remediation_view(
            root,
            durable_snapshot,
            task_id=task_id,
            task_commit=output_task_commit,
        )
    _write_or_print(response, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
