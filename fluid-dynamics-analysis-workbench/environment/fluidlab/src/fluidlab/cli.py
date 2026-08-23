from __future__ import annotations

import argparse
import json
from pathlib import Path

from .loaders import load_config
from .pipeline import run


def _root_from_arg(raw_root: str | None) -> Path:
    if raw_root:
        return Path(raw_root)
    return Path("/app/fluidlab")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fluidlab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--root", default=None)

    show_config = subparsers.add_parser("show-config")
    show_config.add_argument("--root", default=None)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = _root_from_arg(args.root)
    if args.command == "show-config":
        config = load_config(root)
        payload = {
            "system_name": config.system_name,
            "schema_version": config.schema_version,
            "output_dir": str(config.output_dir),
            "csv_fields": config.csv_fields,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.command == "analyze":
        result = run(root)
        print(json.dumps(result, indent=2))
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
