"""Jockey moves. Dispatch occupies dest immediately; confirm does not free origin."""

from __future__ import annotations

import sqlite3
from typing import Optional
from yard.chassis import require_for_move
from yard.codes import MOVE_MISSING, VISIT_MISSING
from yard.inventory import occupy
from yard.move_machine import after_cancel, after_confirm, after_dispatch
from yard.store import fetchone, get_move, get_visit
from yard.visit_ids import make_move_id


def dispatch(con: sqlite3.Connection, visit_id: str, dest_spot_id: str, event_id: str, seq: int) -> tuple[Optional[str], Optional[str]]:
    visit = get_visit(con, visit_id)
    if visit is None:
        return None, VISIT_MISSING
    wheels = require_for_move(con, visit)
    if wheels:
        return None, wheels
    origin = visit["spot_id"]
    move_id = make_move_id(event_id, visit_id)
    con.execute(
        "INSERT INTO moves(move_id, visit_id, state, origin_spot_id, dest_spot_id, event_id, seq) "
        "VALUES (?,?,?,?,?,?,?)",
        (move_id, visit_id, after_dispatch("REQUESTED"), origin, dest_spot_id, event_id, seq),
    )
    occupy(con, dest_spot_id, visit_id)
    con.execute(
        "UPDATE visits SET state = 'MOVING' WHERE visit_id = ?",
        (visit_id,),
    )
    return move_id, None


def confirm(con: sqlite3.Connection, move_id: str) -> Optional[str]:
    move = get_move(con, move_id)
    if move is None:
        return MOVE_MISSING
    dest = str(move["dest_spot_id"])
    occupy(con, dest, str(move["visit_id"]))
    dest_spot = fetchone(con, "SELECT * FROM spots WHERE spot_id = ?", (dest,))
    door_id = None
    state = "ON_YARD"
    if dest_spot is not None and dest_spot["zone"] == "DOCK_APRON":
        door_id = dest_spot["door_id"]
        state = "DOCKED"
    con.execute(
        "UPDATE visits SET state = ?, spot_id = ?, door_id = ? WHERE visit_id = ?",
        (state, dest, door_id, move["visit_id"]),
    )
    con.execute("UPDATE moves SET state = ? WHERE move_id = ?", (after_confirm(str(move["state"])), move_id))
    return None


def cancel(con: sqlite3.Connection, move_id: str) -> Optional[str]:
    move = get_move(con, move_id)
    if move is None:
        return MOVE_MISSING
    con.execute("UPDATE moves SET state = ? WHERE move_id = ?", (after_cancel(str(move["state"])), move_id))
    con.execute(
        "UPDATE visits SET state = 'ON_YARD' WHERE visit_id = ? AND state = 'MOVING'",
        (move["visit_id"],),
    )
    return None
