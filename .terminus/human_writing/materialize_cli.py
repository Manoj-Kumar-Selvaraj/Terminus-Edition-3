#!/usr/bin/env python3
"""Materialize a revision-bound normalized external corpus snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from materialize import CorpusMaterializer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--role-signal", choices=["writer", "reviewer", "both"], required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--cache")
    parser.add_argument("--output")
    args = parser.parse_args()
    materializer = CorpusMaterializer(
        Path(args.root), Path(args.cache).resolve() if args.cache else None
    )
    result = materializer.materialize(
        dataset_id=args.dataset_id,
        input_path=Path(args.input),
        source_revision=args.source_revision,
        role_signal=args.role_signal,
        limit=args.limit,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
