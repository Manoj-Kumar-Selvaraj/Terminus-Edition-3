from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(os.environ.get("WIKI_ROOT", "/app/wiki"))
DB_PATH = Path(os.environ.get("WIKI_DB", str(ROOT / "var" / "wiki.db")))


def connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(DB_PATH)
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=rw", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ping() -> None:
    con = connect()
    try:
        con.execute("SELECT 1").fetchone()
    finally:
        con.close()
