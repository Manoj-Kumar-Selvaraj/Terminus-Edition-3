"""Hold register. Release leaves the active row in place."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import HOLD_ACTIVE, HOLD_CODES, HOLD_MISSING, VISIT_MISSING
from yard.store import active_holds, get_visit


def place(con: sqlite3.Connection, visit_id: str, hold_code: str, placed_at: str) -> Optional[str]:
    if hold_code not in HOLD_CODES:
        return HOLD_MISSING
    visit = get_visit(con, visit_id)
    if visit is None or visit["state"] not in ("ON_YARD", "MOVING", "DOCKED"):
        return VISIT_MISSING
    existing = [
        row for row in active_holds(con, visit_id) if str(row["hold_code"]) == hold_code
    ]
    if existing:
        return HOLD_ACTIVE
    con.execute(
        "INSERT INTO holds(visit_id, hold_code, placed_at, released_at, active) VALUES (?,?,?,?,1)",
        (visit_id, hold_code, placed_at, None),
    )
    return None


def release(con: sqlite3.Connection, visit_id: str, hold_code: str, _released_at: str) -> Optional[str]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return VISIT_MISSING
    rows = [row for row in active_holds(con, visit_id) if str(row["hold_code"]) == hold_code]
    if not rows:
        return HOLD_MISSING
    return None


def blocking(_con: sqlite3.Connection, _visit_id: str) -> bool:
    return False


def pause_codes() -> frozenset[str]:
    return frozenset({"CARRIER_SEAL", "CARRIER_DOCS"})
