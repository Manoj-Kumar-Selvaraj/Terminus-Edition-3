#!/usr/bin/env python3
"""Filter legacy aggregate patch blocks now repaired by dedicated solution assets."""

from __future__ import annotations

import sys
from pathlib import Path

SKIP_EXACT = {
    "lib/common.sh",
    "lib/control.sh",
    "lib/restart.sh",
    "lib/lifecycle.sh",
    "lib/operations.sh",
    "lib/reconcile.sh",
}


def patch_path(header: str) -> str | None:
    if not header.startswith("--- a/"):
        return None
    return header[len("--- a/") :].strip()


def should_skip(path: str | None) -> bool:
    return bool(path and (path in SKIP_EXACT or path.startswith("cobol/")))


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: filter_repair_patch.py INPUT OUTPUT")
    source = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    block: list[str] = []
    current_path: str | None = None
    def flush() -> None:
        nonlocal block, current_path
        if block and not should_skip(current_path):
            out.extend(block)
        block = []
        current_path = None
    for line in source:
        new_path = patch_path(line)
        if new_path is not None:
            flush()
            current_path = new_path
            block = [line]
        elif block:
            block.append(line)
        else:
            out.append(line)
    flush()
    Path(sys.argv[2]).write_text("".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
