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
    from execution.invocation import StageInvocationBuilder
    from execution.ledger import ExecutionLedger
    from execution.record import ExecutionRecordBuilder
    from execution.state import WorkflowStateResolver
    from retrieval.models import InvocationContext
else:
    from .invocation import StageInvocationBuilder
    from .ledger import ExecutionLedger
    from .record import ExecutionRecordBuilder
    from .state import WorkflowStateResolver
    from retrieval.models import InvocationContext


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
    continue_parser.add_argument("--output")
    return parser


def _resolve_state(root: Path, args: argparse.Namespace) -> tuple[WorkflowStateResolver, dict[str, Any]]:
    resolver = WorkflowStateResolver(root)
    freshness = _json_object(args.freshness_json, "--freshness-json") if args.freshness_json else None
    snapshot = resolver.resolve(
        task_id=args.task_id,
        task_commit=args.task_commit,
        control_plane_commit=args.control_plane_commit,
        freshness_overlay=freshness,
    )
    return resolver, snapshot


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
    if next_action["action"] not in {"INVOKE_STAGE", "RETRY_STAGE"}:
        payload["invocation"] = None
        return payload

    stage_id = str(next_action["stage_id"])
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
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()

    if args.command in {"status", "next", "materialize", "continue"}:
        resolver, snapshot = _resolve_state(root, args)
        if args.command == "status":
            _write_or_print(snapshot, args.output)
            return 0
        if args.command == "next":
            _write_or_print(snapshot["next"], args.output)
            return 0 if snapshot["next"]["action"] == "END" else 2
        if args.command == "materialize":
            path = resolver.materialize(snapshot)
            result = {"path": str(path.relative_to(root)), "state": snapshot}
            _write_or_print(result, args.output)
            return 0
        payload = _continue_payload(root, args, snapshot)
        _write_or_print(payload, args.output)
        invocation = payload.get("invocation")
        if isinstance(invocation, dict):
            return 0 if invocation.get("readiness") == "READY" else 2
        return 0 if snapshot["next"]["action"] == "END" else 2

    invocation = _json_object(args.invocation, "--invocation")
    result = _json_object(args.result, "--result")
    record = ExecutionRecordBuilder(root).build(invocation, result)
    authority = record.get("authority")
    if not isinstance(authority, dict):
        raise ValueError("execution record authority is invalid")
    task_id = authority.get("task_id")
    task_commit = authority.get("task_commit")
    control_commit = authority.get("control_plane_commit")
    if not all(isinstance(value, str) and value for value in (task_id, task_commit, control_commit)):
        raise ValueError("record persistence requires task_id, task_commit and control_plane_commit")

    ledger = ExecutionLedger(root, task_id)
    event = ledger.append(record)
    response: dict[str, Any] = {"record": record, "ledger_event": event}
    if not args.no_materialize:
        freshness = _json_object(args.freshness_json, "--freshness-json") if args.freshness_json else None
        resolver = WorkflowStateResolver(root)
        snapshot = resolver.resolve(
            task_id=task_id,
            task_commit=task_commit,
            control_plane_commit=control_commit,
            freshness_overlay=freshness,
        )
        resolver.materialize(snapshot)
        response["state"] = snapshot
    _write_or_print(response, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
