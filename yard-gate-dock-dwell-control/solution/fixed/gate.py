"""Gate-in and gate-out with appointment, seal, identity, hold, and occupancy rules."""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from yard.appointments import claim_appointment, find_appointment
from yard.codes import (
    CONTRACT_MISSING,
    HOLD_BLOCKS_OUT,
    LIVE_TYPES,
    LOADED_TYPES,
    MOVE_IN_FLIGHT,
    SEAL_REQUIRED,
    SPOT_MISSING,
    VISIT_MISSING,
)
from yard.detention import clock_start_iso
from yard.doors import check_eligibility
from yard.holds import blocking
from yard.identity import conflict_open_visit, normalize_equipment, normalize_scac, normalize_trailer, normalize_visit_type
from yard.inventory import check_free, occupy, vacate
from yard.policy import Policy
from yard.store import get_spot, get_visit, upsert_visit
from yard.timeutil import format_instant, parse_instant
from yard.visit_ids import make_visit_id


def _default_on_ground(visit_type: str, explicit: Optional[int]) -> int:
    if explicit is not None:
        return 1 if int(explicit) else 0
    return 1 if visit_type == "DROP_IN" else 0


def gate_in(
    con: sqlite3.Connection,
    policy: Policy,
    flags: dict[str, Any],
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    scac = normalize_scac(str(flags.get("scac") or ""))
    trailer = normalize_trailer(str(flags.get("trailer") or flags.get("trailer_number") or ""))
    visit_type = normalize_visit_type(str(flags.get("visit_type") or ""))
    equipment = normalize_equipment(str(flags.get("equipment") or ""))
    at_iso = str(flags.get("at") or "")
    appointment_id = flags.get("appointment_id")
    spot_id = str(flags.get("spot_id") or "")
    door_id = flags.get("door_id")
    seal = flags.get("seal")
    if not scac or not trailer or not visit_type or not equipment or not at_iso or not spot_id:
        return None, "USAGE"
    minutes, err = policy.require_contract(scac, visit_type)
    if err == CONTRACT_MISSING:
        return None, CONTRACT_MISSING
    if visit_type in LOADED_TYPES and not seal:
        return None, SEAL_REQUIRED
    conflict = conflict_open_visit(con, scac, trailer)
    if conflict:
        return None, conflict
    appointment, aerr = find_appointment(
        con,
        policy,
        scac,
        visit_type,
        trailer,
        at_iso,
        str(door_id) if door_id else None,
        str(appointment_id) if appointment_id else None,
    )
    if aerr:
        return None, aerr
    assert appointment is not None
    spot = get_spot(con, spot_id)
    if spot is None:
        return None, SPOT_MISSING
    if visit_type == "DROP_IN" and str(spot["zone"]) not in ("DROP_LOT", "STAGING"):
        from yard.codes import DOOR_CLASS

        return None, DOOR_CLASS
    door_err = check_eligibility(con, str(door_id) if door_id else None, visit_type, equipment, spot_id)
    if door_err:
        return None, door_err
    busy = check_free(con, spot_id)
    if busy:
        return None, busy
    on_ground = _default_on_ground(visit_type, flags.get("on_ground"))
    visit_id = str(flags.get("visit_id") or make_visit_id(scac, trailer, str(flags.get("event_id") or at_iso)))
    if visit_type in LIVE_TYPES and (door_id or spot["zone"] == "DOCK_APRON"):
        state = "DOCKED"
        door_value = str(door_id) if door_id else spot["door_id"]
    else:
        state = "ON_YARD"
        door_value = None
    occupy_err = occupy(con, spot_id, visit_id)
    if occupy_err:
        return None, occupy_err
    clock_start = clock_start_iso(visit_type, at_iso, appointment, policy)
    upsert_visit(
        con,
        {
            "visit_id": visit_id,
            "scac": scac,
            "trailer_number": trailer,
            "visit_type": visit_type,
            "equipment": equipment,
            "state": state,
            "spot_id": spot_id,
            "door_id": door_value,
            "appointment_id": appointment["appointment_id"],
            "gate_in": format_instant(parse_instant(at_iso)),
            "gate_out": None,
            "seal": seal,
            "on_ground": on_ground,
            "chassis_id": None,
            "clock_start": clock_start,
        },
    )
    claim_appointment(con, str(appointment["appointment_id"]))
    return {
        "visit_id": visit_id,
        "appointment_id": appointment["appointment_id"],
        "state": state,
        "free_minutes": minutes,
    }, None


def gate_out(
    con: sqlite3.Connection,
    flags: dict[str, Any],
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    visit_id = str(flags.get("visit_id") or "")
    at_iso = str(flags.get("at") or "")
    visit = get_visit(con, visit_id)
    if visit is None or visit["state"] == "CLOSED":
        return None, VISIT_MISSING
    if visit["state"] == "MOVING":
        return None, MOVE_IN_FLIGHT
    if blocking(con, visit_id):
        return None, HOLD_BLOCKS_OUT
    seal = flags.get("seal") or visit["seal"]
    if visit["visit_type"] in LOADED_TYPES and not seal:
        return None, SEAL_REQUIRED
    vacate(con, visit["spot_id"], visit_id)
    upsert_visit(
        con,
        {
            **{key: visit[key] for key in visit.keys()},
            "state": "CLOSED",
            "gate_out": format_instant(parse_instant(at_iso)),
            "seal": seal,
            "spot_id": None,
            "door_id": None,
        },
    )
    return {"visit_id": visit_id, "state": "CLOSED"}, None
