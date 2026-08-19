#!/usr/bin/env python3
"""Advisory time-telemetry wrapper around the canonical Terminus controller CLI.

The canonical controller remains the sole workflow-state and routing authority.
This wrapper may attach task-duration telemetry, but elapsed time never blocks a
stage, changes a lifecycle action, or requires a time extension.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.time_budget import TaskTimeBudget
else:
    from .time_budget import TaskTimeBudget


def _write(value: Any, output: str | None = None) -> None:
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

    status = sub.add_parser("status")
    _state_args(status)
    status.add_argument("--output")

    nxt = sub.add_parser("next")
    _state_args(nxt)
    nxt.add_argument("--output")

    cont = sub.add_parser("continue")
    _state_args(cont)
    cont.add_argument("--inputs-json")
    cont.add_argument("--query")
    cont.add_argument("--db")
    cont.add_argument("--retrieval-limit", type=int, default=10)
    cont.add_argument("--max-chars", type=int, default=30000)
    cont.add_argument(
        "--prepare-executor",
        choices=["MANUAL_CHAT", "LOCAL_COMMAND"],
    )
    cont.add_argument("--output")

    record = sub.add_parser("record")
    record.add_argument("--invocation", required=True)
    record.add_argument("--result", required=True)
    record.add_argument("--freshness-json")
    record.add_argument("--no-materialize", action="store_true")
    record.add_argument("--paused-seconds", type=int, default=0)
    record.add_argument("--time-category", default="PLANNED_EXECUTION")
    record.add_argument("--output")

    run = sub.add_parser("record-run")
    run.add_argument("--task-id", required=True)
    run.add_argument("--stage-id", required=True)
    run.add_argument("--seconds", required=True, type=int)
    run.add_argument("--category", default="DETERMINISTIC_VALIDATION")
    run.add_argument("--source", default="EXTERNAL_RUN")
    run.add_argument("--run-ref")
    run.add_argument("--output")

    budget = sub.add_parser("budget")
    budget.add_argument("--task-id", required=True)
    budget.add_argument("--remaining-stages", type=int)
    budget.add_argument("--output")

    # Kept for compatibility with historical automation. It records advisory
    # metadata only and is never required to resume workflow routing.
    extend = sub.add_parser("extend")
    extend.add_argument("--task-id", required=True)
    extend.add_argument("--minutes", required=True, type=int)
    extend.add_argument("--approved-by", required=True)
    extend.add_argument("--reason", default="")
    extend.add_argument("--output")
    return parser


def _controller_path(root: Path) -> Path:
    return root / ".terminus" / "execution" / "controller_cli.py"


def _delegate(root: Path, args: list[str]) -> tuple[int, dict[str, Any]]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        output_path = Path(handle.name)
    try:
        command = [
            sys.executable,
            str(_controller_path(root)),
            "--root",
            str(root),
            *args,
            "--output",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if not output_path.exists() or not output_path.read_text(encoding="utf-8").strip():
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                "canonical controller did not produce JSON output"
                + (f": {detail}" if detail else "")
            )
        value = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("canonical controller output must be one JSON object")
        return completed.returncode, value
    finally:
        output_path.unlink(missing_ok=True)


def _state_cli_args(args: argparse.Namespace, command: str) -> list[str]:
    values = [
        command,
        "--task-id",
        args.task_id,
        "--task-commit",
        args.task_commit,
        "--control-plane-commit",
        args.control_plane_commit,
    ]
    if args.freshness_json:
        values += ["--freshness-json", args.freshness_json]
    return values


def _directive(budget: dict[str, Any]) -> dict[str, Any]:
    guidance_seconds = int(budget["guidance_seconds"])
    consumed_seconds = int(budget["consumed_seconds"])
    if budget["guidance_exceeded"]:
        instruction = (
            "Advisory only: the task has exceeded the seven-hour planning guideline. "
            "Continue the canonical mandatory lifecycle without weakening gates, and avoid "
            "optional or duplicate work where possible."
        )
    else:
        instruction = (
            "Advisory only: aim to complete the task within the seven-hour planning guideline "
            "while preserving every mandatory quality and evidence requirement."
        )
    return {
        "mode": budget["mode"],
        "enforcement": "ADVISORY_ONLY",
        "instruction": instruction,
        "guidance_seconds": guidance_seconds,
        "consumed_seconds": consumed_seconds,
        "guidance_remaining_seconds": max(0, guidance_seconds - consumed_seconds),
        "recommended_next_stage_seconds": None,
    }


def _project(root: Path, task_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    manager = TaskTimeBudget(root, task_id)
    projected = manager.project_workflow(snapshot)
    projected["budget_directive"] = _directive(projected["time_budget"])
    return projected


def _load_task_id_from_invocation(path: str) -> tuple[str, str]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invocation file must contain one JSON object")
    authority = value.get("authority")
    stage = value.get("stage")
    if not isinstance(authority, dict) or not isinstance(stage, dict):
        raise ValueError("invocation is missing authority/stage")
    task_id = authority.get("task_id")
    stage_id = stage.get("stage_id")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("invocation is missing authority.task_id")
    if not isinstance(stage_id, str) or not stage_id:
        raise ValueError("invocation is missing stage.stage_id")
    return task_id, stage_id


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "budget":
        value = TaskTimeBudget(root, args.task_id).snapshot(
            remaining_mandatory_stages=args.remaining_stages
        )
        value["budget_directive"] = _directive(value)
        _write(value, args.output)
        return 0

    if args.command == "extend":
        manager = TaskTimeBudget(root, args.task_id)
        extension = manager.grant_extension(
            args.minutes,
            approved_by=args.approved_by,
            reason=args.reason,
        )
        value = {
            "extension": extension,
            "time_budget": manager.snapshot(),
            "message": (
                "Legacy advisory extension metadata recorded. No time extension is required "
                "for controller routing because task-duration guidance is non-blocking."
            ),
        }
        _write(value, args.output)
        return 0

    if args.command == "record-run":
        manager = TaskTimeBudget(root, args.task_id)
        event = manager.record_run(
            args.stage_id,
            args.seconds,
            category=args.category,
            source=args.source,
            run_ref=args.run_ref,
        )
        value = {
            "time_event": event,
            "time_budget": manager.snapshot(),
        }
        _write(value, args.output)
        return 0

    if args.command in {"status", "next"}:
        rc, snapshot = _delegate(root, _state_cli_args(args, "status"))
        projected = _project(root, args.task_id, snapshot)
        if args.command == "next":
            value = {
                "next": projected["next"],
                "time_budget": projected["time_budget"],
                "budget_directive": projected["budget_directive"],
            }
            _write(value, args.output)
            return 0 if value["next"].get("action") == "END" else 2
        _write(projected, args.output)
        return rc

    if args.command == "continue":
        _, raw_status = _delegate(root, _state_cli_args(args, "status"))
        projected_status = _project(root, args.task_id, raw_status)

        values = _state_cli_args(args, "continue")
        if args.inputs_json:
            values += ["--inputs-json", args.inputs_json]
        if args.query:
            values += ["--query", args.query]
        if args.db:
            values += ["--db", args.db]
        values += ["--retrieval-limit", str(args.retrieval_limit)]
        values += ["--max-chars", str(args.max_chars)]
        if args.prepare_executor:
            values += ["--prepare-executor", args.prepare_executor]
        rc, payload = _delegate(root, values)
        payload["time_budget"] = projected_status["time_budget"]
        payload["budget_directive"] = projected_status["budget_directive"]
        # Do not auto-open a per-stage timer. Telemetry must never become a
        # prerequisite for routing or a source of stale active-span failures.
        _write(payload, args.output)
        return rc

    task_id, stage_id = _load_task_id_from_invocation(args.invocation)
    values = [
        "record",
        "--invocation",
        args.invocation,
        "--result",
        args.result,
    ]
    if args.freshness_json:
        values += ["--freshness-json", args.freshness_json]
    if args.no_materialize:
        values.append("--no-materialize")
    rc, payload = _delegate(root, values)
    if rc == 0:
        manager = TaskTimeBudget(root, task_id)
        active = manager.active_span()
        if active is not None and active.get("stage_id") == stage_id:
            payload["time_event"] = manager.finish(
                paused_seconds=args.paused_seconds,
                category=args.time_category,
            )
        payload["time_budget"] = manager.snapshot()
        payload["budget_directive"] = _directive(payload["time_budget"])
    _write(payload, args.output)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
