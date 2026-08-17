#!/usr/bin/env python3
"""CLI for deterministic dataset-backed instruction-writing calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from human_writing.calibration import HumanWritingCalibrationPlanner
else:
    from .calibration import HumanWritingCalibrationPlanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--output")

    plan = sub.add_parser("plan")
    plan.add_argument("--task-id", required=True)
    plan.add_argument("--domain", required=True)
    plan.add_argument("--output")
    return parser


def write_json(value: object, output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def main() -> int:
    args = build_parser().parse_args()
    planner = HumanWritingCalibrationPlanner(Path(args.root))
    if args.command == "validate":
        write_json(planner.validate(), args.output)
        return 0
    if args.command == "plan":
        write_json(
            planner.build_pair(task_id=args.task_id, domain=args.domain),
            args.output,
        )
        return 0
    raise AssertionError(f"unhandled command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
