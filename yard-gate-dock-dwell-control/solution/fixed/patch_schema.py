"""Patch starter uniqueness: open visits keyed by scac+trailer, not trailer alone."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from yard.paths import Paths


def patch_schema(root: Path | None = None) -> None:
    paths = Paths(root)
    con = sqlite3.connect(str(paths.sqlite))
    con.execute("DROP INDEX IF EXISTS idx_open_trailer")
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_open_scac_trailer "
        "ON visits(scac, trailer_number) WHERE state IN ('ON_YARD','MOVING','DOCKED')"
    )
    con.commit()
    con.close()


if __name__ == "__main__":
    patch_schema()
