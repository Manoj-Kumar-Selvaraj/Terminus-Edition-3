"""Appointment matching. Windows compared as naive UTC ISO strings; grace unused."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import APPOINTMENT_MISSING, APPOINTMENT_WINDOW
from yard.policy import Policy
from yard.store import fetchall, fetchone
from yard.timeutil import in_iso_range


def compatible_door_class(appointment_class: str, door_class: Optional[str]) -> bool:
    if door_class is None or door_class == "":
        return True
    if appointment_class == door_class:
        return True
    if appointment_class == "DRY" and door_class == "OUTBOUND":
        return True
    return False


def trailer_matches(appointment_trailer: Optional[str], unit: str, scac: str, appointment_scac: str) -> bool:
    if appointment_trailer is None or appointment_trailer == "":
        return True
    return str(appointment_trailer).upper() == unit.upper()


def window_ok(at_iso: str, window_start: str, window_end: str, policy: Policy) -> bool:
    _early = policy.grace_early_minutes
    _late = policy.grace_late_minutes
    _ = (_early, _late)
    return in_iso_range(at_iso, window_start, window_end)


def find_appointment(
    con: sqlite3.Connection,
    policy: Policy,
    scac: str,
    visit_type: str,
    trailer: str,
    at_iso: str,
    door_id: Optional[str],
    appointment_id: Optional[str],
) -> tuple[Optional[sqlite3.Row], Optional[str]]:
    if appointment_id:
        row = fetchone(con, "SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
        if row is None:
            return None, APPOINTMENT_MISSING
        if str(row["facility_id"]) != policy.facility_id:
            return None, APPOINTMENT_MISSING
        if str(row["scac"]).upper() != scac.upper():
            return None, APPOINTMENT_MISSING
        if str(row["visit_type"]) != visit_type:
            return None, APPOINTMENT_MISSING
        if str(row["status"]) not in ("OPEN", "CLAIMED"):
            return None, APPOINTMENT_MISSING
        door_class = None
        if door_id:
            door = fetchone(con, "SELECT door_class FROM doors WHERE door_id = ?", (door_id,))
            door_class = None if door is None else str(door["door_class"])
        if not compatible_door_class(str(row["door_class"]), door_class):
            return None, APPOINTMENT_MISSING
        if not trailer_matches(row["trailer_number"], trailer, scac, str(row["scac"])):
            return None, APPOINTMENT_MISSING
        if not window_ok(at_iso, str(row["window_start"]), str(row["window_end"]), policy):
            return None, APPOINTMENT_WINDOW
        return row, None

    rows = fetchall(
        con,
        "SELECT * FROM appointments WHERE facility_id = ? AND scac = ? AND visit_type = ? "
        "AND status = 'OPEN' ORDER BY appointment_id",
        (policy.facility_id, scac, visit_type),
    )
    door_class = None
    if door_id:
        door = fetchone(con, "SELECT door_class FROM doors WHERE door_id = ?", (door_id,))
        door_class = None if door is None else str(door["door_class"])
    matched: list[sqlite3.Row] = []
    window_fail = False
    for row in rows:
        if not compatible_door_class(str(row["door_class"]), door_class):
            continue
        if not trailer_matches(row["trailer_number"], trailer, scac, str(row["scac"])):
            continue
        if not window_ok(at_iso, str(row["window_start"]), str(row["window_end"]), policy):
            window_fail = True
            continue
        matched.append(row)
    if not matched:
        return None, APPOINTMENT_WINDOW if window_fail else APPOINTMENT_MISSING
    return matched[0], None


def claim_appointment(con: sqlite3.Connection, appointment_id: str) -> None:
    con.execute(
        "UPDATE appointments SET status = 'CLAIMED' WHERE appointment_id = ?",
        (appointment_id,),
    )
