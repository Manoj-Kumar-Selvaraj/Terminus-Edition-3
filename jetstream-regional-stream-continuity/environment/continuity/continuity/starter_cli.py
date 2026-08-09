"""Operator CLI binding for the inherited continuity controller."""

from __future__ import annotations

from collections.abc import Sequence

from . import cli as _cli
from .engine import ContinuityEngine

_cli.ContinuityEngine = ContinuityEngine


def main(argv: Sequence[str] | None = None) -> int:
    return _cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
