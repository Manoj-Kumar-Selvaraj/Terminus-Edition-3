"""Detention clock: live max(window_start, gate_in), yard-hold pauses, whole minutes."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

from yard.codes import LIVE_TYPES
from yard.holds import pause_codes
from yard.interval import covered_minutes
from yard.policy import Policy
from yard.records import HoldRecord
from yard.store import fetchall, get_appointment, get_visit
from yard.timeutil import format_instant, minutes_between, parse_instant, whole_minutes


def clock_start_for(visit: sqlite3.Row, appointment: Optional[sqlite3.Row], policy: Policy) -> datetime:
    gate_in = parse_instant(str(visit["gate_in"]))
    if str(visit["visit_type"]) not in LIVE_TYPES:
        return gate_in
    if appointment is None:
        return gate_in
    window_start = parse_instant(str(appointment["window_start"]))
    return window_start if window_start > gate_in else gate_in


def clock_start_iso(visit_type: str, gate_in_iso: str, appointment: sqlite3.Row, _policy: Policy) -> str:
    gate_in = parse_instant(gate_in_iso)
    if visit_type not in LIVE_TYPES:
        return format_instant(gate_in)
    window_start = parse_instant(str(appointment["window_start"]))
    start = window_start if window_start > gate_in else gate_in
    return format_instant(start)


def pause_minutes(con: sqlite3.Connection, visit_id: str, start: datetime, end: datetime) -> float:
    codes = pause_codes()
    intervals: list[tuple[datetime, datetime]] = []
    rows = fetchall(
        con,
        "SELECT * FROM holds WHERE visit_id = ? ORDER BY placed_at",
        (visit_id,),
    )
    for raw in rows:
        record = HoldRecord.from_row(raw)
        if record.hold_code not in codes:
            continue
        placed = parse_instant(record.placed_at)
        released = parse_instant(record.released_at) if record.released_at else end
        intervals.append((placed, released))
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
    start = clock_start_for(visit, appointment, policy)
    free, err = policy.free_minutes(str(visit["scac"]), str(visit["visit_type"]))
    if err or free is None:
        free = 0
    end = parse_instant(str(visit["gate_out"])) if visit["gate_out"] else as_of
    paused = pause_minutes(con, str(visit["visit_id"]), start, end)
    elapsed = minutes_between(start, end) - paused
    raw = elapsed - float(free)
    status = "CLOSED" if visit["state"] == "CLOSED" else "OPEN"
    return {
        "visit_id": visit["visit_id"],
        "scac": visit["scac"],
        "visit_type": visit["visit_type"],
        "clock_start": format_instant(start),
        "free_minutes": int(free),
        "pause_minutes": whole_minutes(paused),
        "chargeable_minutes": whole_minutes(raw),
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
