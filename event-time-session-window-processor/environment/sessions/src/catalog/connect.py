from __future__ import annotations

import sqlite3
from pathlib import Path

from src.catalog.names import CATALOG_PATH


def catalog_exists(path: Path | None = None) -> bool:
    target = path or CATALOG_PATH
    return target.is_file() and target.stat().st_size > 0


def connect_catalog(path: Path | None = None, *, readonly: bool = True) -> sqlite3.Connection:
    target = path or CATALOG_PATH
    if not target.is_file():
        raise FileNotFoundError(f"operator catalog missing: {target}")
    posix = target.resolve().as_posix()
    if readonly:
        con = sqlite3.connect(f"file:{posix}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(posix)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def scalar(con: sqlite3.Connection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def table_names(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def column_names(con: sqlite3.Connection, table: str) -> list[str]:
    rows = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [str(row[1]) for row in rows]
