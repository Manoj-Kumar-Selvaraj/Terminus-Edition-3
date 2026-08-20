#!/usr/bin/env python3
"""Machine interface for durable Terminus human decision gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from human_decision import HumanDecisionStore


def _json_object(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("--context-json must contain one JSON object")
    return value


def _emit(value: Any) -> None:
    sys.stdout.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    request = sub.add_parser("request")
    request.add_argument("--task-id", required=True)
    request.add_argument("--task-commit", required=True)
    request.add_argument("--stage", required=True)
    request.add_argument("--decision-type", required=True)
    request.add_argument("--allow", action="append", dest="allowed", required=True)
    request.add_argument("--reason", required=True)
    request.add_argument("--consequences", required=True)
    request.add_argument("--context-json")

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--decision-id", required=True)
    resolve.add_argument("--decision", required=True)
    resolve.add_argument("--response-text", required=True)

    status = sub.add_parser("status")
    status.add_argument("--task-id", required=True)
    status.add_argument("--task-commit")

    show = sub.add_parser("show")
    show.add_argument("--decision-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = HumanDecisionStore(Path(args.root))
    if args.command == "request":
        event = store.request(
            task_id=args.task_id,
            task_commit=args.task_commit,
            stage=args.stage,
            decision_type=args.decision_type,
            allowed_decisions=args.allowed,
            reason=args.reason,
            consequences=args.consequences,
            context=_json_object(args.context_json),
        )
        request = event["request"]
        _emit(
            {
                "status": "HUMAN_DECISION_REQUIRED" if event.get("resolution") is None else "RESOLVED",
                "execution_mode": "CHAT_HUMAN_APPROVAL",
                "decision": request,
                "response_policy": (
                    "Present the bounded decision to the human in the active task chat. "
                    "Do not infer approval from earlier prose. Resolve only after an explicit response."
                ),
            }
        )
        return 2 if event.get("resolution") is None else 0
    if args.command == "resolve":
        event = store.resolve(
            decision_id=args.decision_id,
            decision=args.decision,
            response_text=args.response_text,
        )
        _emit({"status": "RESOLVED", "execution_mode": "CHAT_HUMAN_APPROVAL", "event": event})
        return 0
    if args.command == "status":
        pending = store.outstanding(task_id=args.task_id, task_commit=args.task_commit)
        _emit(
            {
                "status": "HUMAN_DECISION_REQUIRED" if pending else "NO_OUTSTANDING_HUMAN_DECISION",
                "execution_mode": "CHAT_HUMAN_APPROVAL" if pending else None,
                "outstanding": pending,
            }
        )
        return 2 if pending else 0
    event = store.get(args.decision_id)
    if event is None:
        _emit({"status": "NOT_FOUND", "decision_id": args.decision_id})
        return 2
    _emit({"status": "RESOLVED" if event.get("resolution") else "HUMAN_DECISION_REQUIRED", "event": event})
    return 0 if event.get("resolution") else 2


if __name__ == "__main__":
    raise SystemExit(main())
