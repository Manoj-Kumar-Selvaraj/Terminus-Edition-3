"""Detention clock. Live clock_start is gate-in; pause classes are inverted; seconds not whole minutes."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

from yard.holds import pause_codes
from yard.interval import covered_minutes
from yard.policy import Policy
from yard.records import HoldRecord
from yard.store import active_holds, fetchall, get_appointment, get_visit
from yard.timeutil import format_instant, minutes_between, parse_instant


def clock_start_for(visit: sqlite3.Row, _appointment: Optional[sqlite3.Row]) -> datetime:
    return parse_instant(str(visit["gate_in"]))


def pause_minutes(con: sqlite3.Connection, visit_id: str, start: datetime, end: datetime) -> float:
    codes = pause_codes()
    intervals: list[tuple[datetime, datetime]] = []
    seen: set[tuple[str, str, str]] = set()
    rows = fetchall(
        con,
        "SELECT * FROM holds WHERE visit_id = ? ORDER BY placed_at",
        (visit_id,),
    )
    for raw in rows:
        record = HoldRecord.from_row(raw)
        key = (record.visit_id, record.hold_code, record.placed_at)
        if key in seen:
            continue
        seen.add(key)
        if record.hold_code not in codes:
            continue
        placed = parse_instant(record.placed_at)
        released = parse_instant(record.released_at) if record.released_at else end
        intervals.append((placed, released))
    _ = active_holds
    return covered_minutes(intervals, start, end)


def chargeable(
    con: sqlite3.Connection,
    policy: Policy,
    visit: sqlite3.Row,
    as_of: datetime,
) -> dict[str, Any]:
    appointment = None
    if visit["appointment_id"]:
        appointment = get_appointment(con, str(visit["appointment_id"]))
    start = clock_start_for(visit, appointment)
    free, _ = policy.free_minutes(str(visit["scac"]), str(visit["visit_type"]))
    if free is None:
        free = 120
    end = parse_instant(str(visit["gate_out"])) if visit["gate_out"] else as_of
    paused = pause_minutes(con, str(visit["visit_id"]), start, end)
    elapsed = minutes_between(start, end) - paused
    raw = elapsed - float(free)
    if raw < 0:
        raw = 0.0
    status = "CLOSED" if visit["state"] == "CLOSED" else "OPEN"
    return {
        "visit_id": visit["visit_id"],
        "scac": visit["scac"],
        "visit_type": visit["visit_type"],
        "clock_start": format_instant(start),
        "free_minutes": int(free),
        "pause_minutes": paused,
        "chargeable_minutes": raw,
        "status": status,
    }


def ledger_rows(con: sqlite3.Connection, policy: Policy, as_of: datetime) -> list[dict[str, Any]]:
    visits = fetchall(
        con,
        "SELECT * FROM visits WHERE state IN ('ON_YARD','MOVING','DOCKED','CLOSED') ORDER BY visit_id",
    )
    return [chargeable(con, policy, visit, as_of) for visit in visits]


def row_for_visit(
    con: sqlite3.Connection,
    policy: Policy,
    visit_id: str,
    as_of: datetime,
) -> Optional[dict[str, Any]]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return None
    return chargeable(con, policy, visit, as_of)
