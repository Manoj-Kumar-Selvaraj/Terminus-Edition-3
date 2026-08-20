#!/usr/bin/env python3
"""Execute one packet-bound Terminus Q4/Q6/Q8 review with one selected backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.quality_execution_guard import install_quality_execution_guards

    install_quality_execution_guards()
    from execution.quality_executor import QualityExecutorError, execute_quality_packet
else:
    from .quality_execution_guard import install_quality_execution_guards

    install_quality_execution_guards()
    from .quality_executor import QualityExecutorError, execute_quality_packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--packet", required=True)
    parser.add_argument("--executor", required=True, choices=["cursor", "api"])
    parser.add_argument("--provider", choices=["openai", "anthropic"])
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=2700)
    parser.add_argument("--publish-result", action="store_true")
    parser.add_argument(
        "--review-output",
        help="copy the validated canonical review to this CI/artifact path",
    )
    parser.add_argument(
        "--diagnostic-output",
        help="Cursor only: persist the sanitized terminal result event, never thinking events",
    )
    parser.add_argument("--output", help="write the executor summary JSON to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = execute_quality_packet(
            Path(args.root),
            args.packet,
            executor=args.executor,
            provider=args.provider,
            model=args.model,
            timeout_seconds=args.timeout,
            publish_result=args.publish_result,
            review_copy_path=Path(args.review_output) if args.review_output else None,
            diagnostic_path=Path(args.diagnostic_output) if args.diagnostic_output else None,
        )
    except (QualityExecutorError, OSError, ValueError) as exc:
        print(f"quality executor failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
