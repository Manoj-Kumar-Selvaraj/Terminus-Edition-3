"""Operator CLI binding for the inherited continuity controller."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from . import cli as _cli
from .engine import ContinuityEngine

_cli.ContinuityEngine = ContinuityEngine
_original_ensure_database = _cli.ensure_database


def _ensure_database(root: Path, *, reset: bool = False) -> Path:
    database = _original_ensure_database(root, reset=reset)
    extension = root / "sql" / "runtime_extensions.sql"
    if extension.exists():
        connection = sqlite3.connect(database)
        try:
            connection.executescript(extension.read_text(encoding="utf-8"))
            connection.commit()
        finally:
            connection.close()
    return database


_cli.ensure_database = _ensure_database


def main(argv: Sequence[str] | None = None) -> int:
    return _cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
