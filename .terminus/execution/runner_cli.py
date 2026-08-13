#!/usr/bin/env python3
"""Prepare manual handoffs or run a shell-free local Terminus stage executor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.executor import ExecutorMode
    from execution.runner import ExecutorRunner
else:
    from .executor import ExecutorMode
    from .runner import ExecutorRunner


def _json_object(path: str, label: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def _write_json(value: object, output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser(
        "prepare",
        help="compile an executor handoff without executing or mutating workflow state",
    )
    prepare.add_argument("--invocation", required=True)
    prepare.add_argument(
        "--executor",
        choices=[mode.value for mode in ExecutorMode],
        default=ExecutorMode.MANUAL_CHAT.value,
    )
    prepare.add_argument(
        "--text",
        action="store_true",
        help="print only the MANUAL_CHAT paste-ready handoff text",
    )
    prepare.add_argument("--output")

    local = sub.add_parser(
        "run-local",
        help="execute an argv command with handoff JSON on stdin; never records state",
    )
    local.add_argument("--invocation", required=True)
    local.add_argument("--timeout", type=int, default=600)
    local.add_argument(
        "--inherit-env",
        action="store_true",
        help="inherit the complete current environment instead of the safe allowlist",
    )
    local.add_argument("--output")
    local.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="command argv after --, for example: -- python executor.py",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    invocation = _json_object(args.invocation, "--invocation")
    runner = ExecutorRunner(root)

    if args.command == "prepare":
        prepared = runner.prepare(invocation, executor_mode=args.executor)
        if args.text:
            if args.executor != ExecutorMode.MANUAL_CHAT.value:
                raise ValueError("--text is valid only with MANUAL_CHAT")
            text = prepared["handoff"]["handoff_text"]
            if args.output:
                target = Path(args.output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(text), encoding="utf-8")
            else:
                sys.stdout.write(str(text))
        else:
            _write_json(prepared, args.output)
        return 0

    command_argv = list(args.argv)
    if command_argv and command_argv[0] == "--":
        command_argv = command_argv[1:]
    response = runner.run_local(
        invocation,
        command_argv,
        timeout_seconds=args.timeout,
        inherit_environment=args.inherit_env,
    )
    _write_json(response, args.output)
    return 0 if response["status"] == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
