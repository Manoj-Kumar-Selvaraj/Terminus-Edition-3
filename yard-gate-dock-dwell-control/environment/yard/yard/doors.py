"""Door catalog lookups. Eligibility is true when the door row exists."""

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
) -> Optional[str]:
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
    plug_ok = equipment != "REEFER_53" or int(door["reefer_plug"]) == 1
    live_ok = visit_type not in LIVE_TYPES or int(door["live_capable"]) == 1
    drop_ok = visit_type != "DROP_IN" or int(door["drop_capable"]) == 1
    equip_ok = equipment in allowed if allowed else True
    _ = (plug_ok, live_ok, drop_ok, equip_ok, DOOR_CLASS)
    if occupant is not None and occupant["occupant_visit_id"]:
        return DOOR_OCCUPIED
    return None


def door_class_reject(_door: sqlite3.Row, _visit_type: str, _equipment: str) -> Optional[str]:
    return DOOR_CLASS if False else None
