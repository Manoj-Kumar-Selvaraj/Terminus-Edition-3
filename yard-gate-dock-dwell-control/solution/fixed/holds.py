"""Hold register with class semantics, gate-out blocking, and real release."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import HOLD_ACTIVE, HOLD_CODES, HOLD_MISSING, VISIT_MISSING
from yard.store import active_holds, get_visit

PAUSE = frozenset({"YARD_OSND", "YARD_SAFETY"})


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


def release(con: sqlite3.Connection, visit_id: str, hold_code: str, released_at: str) -> Optional[str]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return VISIT_MISSING
    rows = [row for row in active_holds(con, visit_id) if str(row["hold_code"]) == hold_code]
    if not rows:
        return HOLD_MISSING
    con.execute(
        "UPDATE holds SET active = 0, released_at = ? WHERE visit_id = ? AND hold_code = ? AND active = 1",
        (released_at, visit_id, hold_code),
    )
    return None


def blocking(con: sqlite3.Connection, visit_id: str) -> bool:
    return bool(active_holds(con, visit_id))


def pause_codes() -> frozenset[str]:
    return PAUSE
