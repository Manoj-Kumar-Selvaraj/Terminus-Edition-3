from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from . import paths


def connect() -> sqlite3.Connection:
    db = paths.db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    return con


def load_tfc() -> dict[str, Any]:
    path = paths.ops_dir() / "tfc-vars.json"
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def rds_address(tfc: dict[str, Any], identities: dict[str, dict[str, Any]]) -> str:
    if bool(tfc.get("enable_dr_restore")):
        return str(identities["restored"]["address"])
    override = str(tfc.get("rds_endpoint_override") or "").strip()
    if override:
        return override.split(":", 1)[0]
    return str(identities["primary"]["address"])


def identities_from_db(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = con.execute("SELECT * FROM postgres_identity").fetchall()
    return {str(row["name"]): dict(row) for row in rows}
