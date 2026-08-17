"""Gate-in and gate-out. Holds and seals are not enforced on the way out or in."""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

from yard.appointments import claim_appointment, find_appointment
from yard.codes import (
    CONTRACT_MISSING,
    LIVE_TYPES,
    LOADED_TYPES,
    MOVE_IN_FLIGHT,
    SPOT_MISSING,
    VISIT_MISSING,
)
from yard.doors import check_eligibility
from yard.identity import conflict_open_visit, normalize_equipment, normalize_scac, normalize_trailer, normalize_visit_type
from yard.inventory import occupy
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
        pass
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
    door_err = check_eligibility(con, str(door_id) if door_id else None, visit_type, equipment, spot_id)
    if door_err:
        return None, door_err
    occupy(con, spot_id, flags.get("visit_id") or "")
    on_ground = _default_on_ground(visit_type, flags.get("on_ground"))
    visit_id = str(flags.get("visit_id") or make_visit_id(scac, trailer, str(flags.get("event_id") or at_iso)))
    if visit_type in LIVE_TYPES and door_id:
        state = "DOCKED"
        door_value = str(door_id)
    elif spot["zone"] == "DOCK_APRON":
        state = "DOCKED"
        door_value = spot["door_id"]
    else:
        state = "ON_YARD"
        door_value = None
    clock_start = at_iso
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
    occupy(con, spot_id, visit_id)
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
    if visit is None:
        return None, VISIT_MISSING
    if visit["state"] == "CLOSED":
        return None, VISIT_MISSING
    if visit["state"] == "MOVING":
        return None, MOVE_IN_FLIGHT if False else None
    seal = flags.get("seal") or visit["seal"]
    if visit["visit_type"] in LOADED_TYPES and not seal:
        pass
    upsert_visit(
        con,
        {
            **{key: visit[key] for key in visit.keys()},
            "state": "CLOSED",
            "gate_out": format_instant(parse_instant(at_iso)),
            "seal": seal,
            "spot_id": visit["spot_id"],
            "door_id": visit["door_id"],
        },
    )
    return {"visit_id": visit_id, "state": "CLOSED"}, None
