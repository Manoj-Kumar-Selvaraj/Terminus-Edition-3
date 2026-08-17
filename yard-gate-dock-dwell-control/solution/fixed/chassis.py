"""Chassis pool mount/dismount. Grounded drop equipment cannot roll without wheels."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import CHASSIS_BUSY, CHASSIS_MISSING, CHASSIS_REQUIRED, DROP_EQUIPMENT, VISIT_MISSING
from yard.store import fetchone, get_chassis, get_visit


def needs_wheels(visit: sqlite3.Row) -> bool:
    if int(visit["on_ground"] or 0) != 1:
        return False
    return str(visit["equipment"]) in DROP_EQUIPMENT


def require_for_move(_con: sqlite3.Connection, visit: sqlite3.Row) -> Optional[str]:
    if needs_wheels(visit) and not visit["chassis_id"]:
        return CHASSIS_REQUIRED
    return None


def mount(con: sqlite3.Connection, visit_id: str, chassis_id: str) -> Optional[str]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return VISIT_MISSING
    chassis = get_chassis(con, chassis_id)
    if chassis is None:
        return CHASSIS_MISSING
    mounted = chassis["mounted_visit_id"]
    if mounted and mounted != visit_id:
        return CHASSIS_BUSY
    con.execute(
        "UPDATE chassis_units SET mounted_visit_id = ?, spot_id = NULL WHERE chassis_id = ?",
        (visit_id, chassis_id),
    )
    con.execute(
        "UPDATE visits SET chassis_id = ?, on_ground = 0 WHERE visit_id = ?",
        (chassis_id, visit_id),
    )
    return None


def dismount(con: sqlite3.Connection, visit_id: str) -> Optional[str]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return VISIT_MISSING
    chassis_id = visit["chassis_id"]
    if chassis_id:
        stack = fetchone(
            con,
            "SELECT spot_id FROM spots WHERE zone = 'CHASSIS_STACK' AND occupant_visit_id IS NULL "
            "AND reserved_move_id IS NULL ORDER BY spot_id LIMIT 1",
        )
        con.execute(
            "UPDATE chassis_units SET mounted_visit_id = NULL, spot_id = ? WHERE chassis_id = ?",
            (None if stack is None else stack["spot_id"], chassis_id),
        )
    con.execute(
        "UPDATE visits SET chassis_id = NULL, on_ground = 1 WHERE visit_id = ?",
        (visit_id,),
    )
    return None
