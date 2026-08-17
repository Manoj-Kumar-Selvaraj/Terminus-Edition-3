"""Door catalog lookups with class, plug, live/drop, and equipment constraints."""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from yard.codes import DOOR_CLASS, DOOR_MISSING, DOOR_OCCUPIED, LIVE_TYPES
from yard.store import fetchone, get_door, get_spot


def allowed_equipment_list(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def door_for_apron(con: sqlite3.Connection, spot_id: str) -> Optional[sqlite3.Row]:
    spot = get_spot(con, spot_id)
    if spot is None or spot["zone"] != "DOCK_APRON" or not spot["door_id"]:
        return None
    return get_door(con, str(spot["door_id"]))


def check_eligibility(
    con: sqlite3.Connection,
    door_id: Optional[str],
    visit_type: str,
    equipment: str,
    spot_id: Optional[str],
    ignore_visit_id: Optional[str] = None,
) -> Optional[str]:
    if visit_type == "DROP_IN" and spot_id:
        spot = get_spot(con, spot_id)
        if spot is not None and str(spot["zone"]) == "DOCK_APRON":
            return DOOR_CLASS
    target_door_id = door_id
    if target_door_id is None and spot_id:
        spot = get_spot(con, spot_id)
        if spot is not None and spot["door_id"]:
            target_door_id = str(spot["door_id"])
    if target_door_id is None:
        return None
    door = get_door(con, target_door_id)
    if door is None:
        return DOOR_MISSING
    occupant = fetchone(
        con,
        "SELECT occupant_visit_id FROM spots WHERE door_id = ? AND zone = 'DOCK_APRON'",
        (target_door_id,),
    )
    allowed = allowed_equipment_list(str(door["allowed_equipment"]))
    if equipment == "REEFER_53" and int(door["reefer_plug"]) != 1:
        return DOOR_CLASS
    if visit_type in LIVE_TYPES and int(door["live_capable"]) != 1:
        return DOOR_CLASS
    if visit_type == "DROP_IN" and int(door["drop_capable"]) != 1:
        return DOOR_CLASS
    if allowed and equipment not in allowed:
        return DOOR_CLASS
    occupant_id = None if occupant is None else occupant["occupant_visit_id"]
    if occupant_id and occupant_id != ignore_visit_id:
        return DOOR_OCCUPIED
    return None
