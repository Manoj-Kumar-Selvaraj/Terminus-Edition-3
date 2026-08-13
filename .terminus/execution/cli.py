#!/usr/bin/env python3
"""Build one bounded Terminus stage invocation packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.invocation import StageInvocationBuilder
    from retrieval.models import InvocationContext
else:
    from .invocation import StageInvocationBuilder
    from retrieval.models import InvocationContext


def _key_values(values: list[str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=VALUE: {value}")
        key, item = value.split("=", 1)
        if not key:
            raise ValueError(f"empty key in {value}")
        output[key] = item
    return output


def _input_values(path: str | None, values: list[str]) -> dict[str, object]:
    output: dict[str, object] = {}
    if path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("--inputs-json must contain one JSON object")
        output.update(payload)
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=JSON: {value}")
        key, raw = value.split("=", 1)
        if not key:
            raise ValueError(f"empty input name in {value}")
        output[key] = json.loads(raw)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--db")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--control-plane-commit", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--task-commit")
    parser.add_argument("--role-contract-hash")
    parser.add_argument("--packet-binding")
    parser.add_argument("--review-scope-hash")
    parser.add_argument("--ci-run-id")
    parser.add_argument("--policy-version", action="append", default=[])
    parser.add_argument("--allow-evidence", action="append", default=[])
    parser.add_argument("--exclude-evidence", action="append", default=[])
    parser.add_argument("--allow-sensitivity", action="append", default=[])
    parser.add_argument("--inputs-json")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help='declared stage input as NAME=JSON, for example --input CREATION_REQUEST="create a task"',
    )
    parser.add_argument("--query")
    parser.add_argument("--retrieval-limit", type=int, default=10)
    parser.add_argument("--max-chars", type=int, default=30000)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    allowed = frozenset(args.allow_evidence) if args.allow_evidence else None
    sensitivities = (
        frozenset(args.allow_sensitivity) if args.allow_sensitivity else None
    )
    context = InvocationContext(
        stage_id=args.stage,
        role_id=args.role,
        task_id=args.task_id,
        task_commit=args.task_commit,
        control_plane_commit=args.control_plane_commit,
        role_contract_hash=args.role_contract_hash,
        packet_binding=args.packet_binding,
        review_scope_hash=args.review_scope_hash,
        ci_run_id=args.ci_run_id,
        policy_versions=_key_values(args.policy_version),
        allowed_evidence_classes=allowed,
        excluded_evidence_classes=frozenset(args.exclude_evidence),
        allowed_sensitivities=sensitivities,
    )
    inputs = _input_values(args.inputs_json, args.input)
    packet = StageInvocationBuilder(root).build(
        context,
        inputs,
        retrieval_query=args.query,
        retrieval_db=Path(args.db).resolve() if args.db else None,
        retrieval_limit=args.retrieval_limit,
        max_chars=args.max_chars,
    )
    rendered = json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if packet["readiness"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
