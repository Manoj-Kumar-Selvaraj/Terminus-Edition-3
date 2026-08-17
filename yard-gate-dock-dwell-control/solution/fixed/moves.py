"""Jockey moves with in-transit vacancy and dest reservation."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.chassis import require_for_move
from yard.codes import MOVE_MISSING, VISIT_MISSING
from yard.doors import check_eligibility
from yard.inventory import check_free, clear_reservation, occupy, reserve_dest, vacate
from yard.move_machine import after_cancel, after_confirm, after_dispatch
from yard.store import get_move, get_spot, get_visit
from yard.visit_ids import make_move_id


def dispatch(con: sqlite3.Connection, visit_id: str, dest_spot_id: str, event_id: str, seq: int) -> tuple[Optional[str], Optional[str]]:
    visit = get_visit(con, visit_id)
    if visit is None or visit["state"] not in ("ON_YARD", "DOCKED"):
        return None, VISIT_MISSING
    wheels = require_for_move(con, visit)
    if wheels:
        return None, wheels
    dest = get_spot(con, dest_spot_id)
    if dest is None:
        return None, check_free(con, dest_spot_id)
    err = check_eligibility(
        con,
        str(dest["door_id"]) if dest["door_id"] else None,
        str(visit["visit_type"]),
        str(visit["equipment"]),
        dest_spot_id,
        ignore_visit_id=visit_id,
    )
    if err:
        return None, err
    busy = check_free(con, dest_spot_id)
    if busy:
        return None, busy
    origin = visit["spot_id"]
    move_id = make_move_id(event_id, visit_id)
    reserved = reserve_dest(con, dest_spot_id, move_id)
    if reserved:
        return None, reserved
    if origin:
        vacate(con, str(origin), visit_id)
    con.execute(
        "INSERT INTO moves(move_id, visit_id, state, origin_spot_id, dest_spot_id, event_id, seq) "
        "VALUES (?,?,?,?,?,?,?)",
        (move_id, visit_id, after_dispatch("REQUESTED"), origin, dest_spot_id, event_id, seq),
    )
    con.execute(
        "UPDATE visits SET state = 'MOVING', spot_id = NULL, door_id = NULL WHERE visit_id = ?",
        (visit_id,),
    )
    return move_id, None


def confirm(con: sqlite3.Connection, move_id: str) -> Optional[str]:
    move = get_move(con, move_id)
    if move is None or str(move["state"]) != "IN_TRANSIT":
        return MOVE_MISSING
    dest = str(move["dest_spot_id"])
    visit_id = str(move["visit_id"])
    err = occupy(con, dest, visit_id, allow_reserved_for=move_id)
    if err:
        return err
    clear_reservation(con, dest, move_id)
    dest_spot = get_spot(con, dest)
    door_id = None
    state = "ON_YARD"
    if dest_spot is not None and dest_spot["zone"] == "DOCK_APRON":
        door_id = dest_spot["door_id"]
        state = "DOCKED"
    con.execute(
        "UPDATE visits SET state = ?, spot_id = ?, door_id = ? WHERE visit_id = ?",
        (state, dest, door_id, visit_id),
    )
    con.execute("UPDATE moves SET state = ? WHERE move_id = ?", (after_confirm("IN_TRANSIT"), move_id))
    return None


def cancel(con: sqlite3.Connection, move_id: str) -> Optional[str]:
    move = get_move(con, move_id)
    if move is None or str(move["state"]) != "IN_TRANSIT":
        return MOVE_MISSING
    origin = move["origin_spot_id"]
    dest = move["dest_spot_id"]
    visit_id = str(move["visit_id"])
    clear_reservation(con, str(dest) if dest else None, move_id)
    door_id = None
    state = "ON_YARD"
    if origin:
        err = occupy(con, str(origin), visit_id)
        if err:
            return err
        origin_spot = get_spot(con, str(origin))
        if origin_spot is not None and origin_spot["zone"] == "DOCK_APRON":
            door_id = origin_spot["door_id"]
            state = "DOCKED"
    con.execute("UPDATE moves SET state = ? WHERE move_id = ?", (after_cancel("IN_TRANSIT"), move_id))
    con.execute(
        "UPDATE visits SET state = ?, spot_id = ?, door_id = ? WHERE visit_id = ?",
        (state, origin, door_id, visit_id),
    )
    return None
