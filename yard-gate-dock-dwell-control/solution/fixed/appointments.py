"""Appointment matching in yard local time with grace; pool slots are SCAC-only."""

from __future__ import annotations

from datetime import timedelta
import sqlite3
from typing import Optional

from yard.codes import APPOINTMENT_MISSING, APPOINTMENT_WINDOW
from yard.policy import Policy
from yard.store import fetchall, fetchone
from yard.timeutil import parse_instant, to_local


def compatible_door_class(appointment_class: str, door_class: Optional[str]) -> bool:
    if door_class is None or door_class == "":
        return True
    if appointment_class == door_class:
        return True
    if appointment_class == "DRY" and door_class == "OUTBOUND":
        return True
    return False


def trailer_matches(appointment_trailer: Optional[str], unit: str, scac: str, appointment_scac: str) -> bool:
    if str(appointment_scac).upper() != scac.upper():
        return False
    if appointment_trailer is None or appointment_trailer == "":
        return True
    return str(appointment_trailer).upper() == unit.upper()


def window_ok(at_iso: str, window_start: str, window_end: str, policy: Policy) -> bool:
    at_local = to_local(parse_instant(at_iso), policy.yard_tz)
    start_local = to_local(parse_instant(window_start), policy.yard_tz)
    end_local = to_local(parse_instant(window_end), policy.yard_tz)
    early = start_local - timedelta(minutes=int(policy.grace_early_minutes))
    late = end_local + timedelta(minutes=int(policy.grace_late_minutes))
    return early <= at_local <= late


def identity_ok(row: sqlite3.Row, policy: Policy, scac: str, visit_type: str, trailer: str, door_class: Optional[str]) -> bool:
    if str(row["facility_id"]) != policy.facility_id:
        return False
    if str(row["scac"]).upper() != scac.upper():
        return False
    if str(row["visit_type"]) != visit_type:
        return False
    if str(row["status"]) != "OPEN":
        return False
    if not compatible_door_class(str(row["door_class"]), door_class):
        return False
    if not trailer_matches(row["trailer_number"], trailer, scac, str(row["scac"])):
        return False
    return True


def _door_class(con: sqlite3.Connection, door_id: Optional[str]) -> Optional[str]:
    if not door_id:
        return None
    door = fetchone(con, "SELECT door_class FROM doors WHERE door_id = ?", (door_id,))
    return None if door is None else str(door["door_class"])


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
    door_class = _door_class(con, door_id)
    if appointment_id:
        row = fetchone(con, "SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
        if row is None or not identity_ok(row, policy, scac, visit_type, trailer, door_class):
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
    matched: list[sqlite3.Row] = []
    window_fail = False
    for row in rows:
        if not identity_ok(row, policy, scac, visit_type, trailer, door_class):
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
