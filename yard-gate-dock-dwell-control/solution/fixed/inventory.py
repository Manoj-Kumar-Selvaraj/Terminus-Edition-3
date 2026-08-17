"""Exclusive spot occupancy plus dest-spot reservations for in-transit moves."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import SPOT_MISSING, SPOT_OCCUPIED
from yard.store import get_spot, set_spot_occupant


def occupy(con: sqlite3.Connection, spot_id: str, visit_id: str, allow_reserved_for: Optional[str] = None) -> Optional[str]:
    spot = get_spot(con, spot_id)
    if spot is None:
        return SPOT_MISSING
    occupant = spot["occupant_visit_id"]
    reserved = spot["reserved_move_id"]
    if occupant and occupant != visit_id:
        return SPOT_OCCUPIED
    if reserved and allow_reserved_for is not None and reserved != allow_reserved_for:
        return SPOT_OCCUPIED
    if reserved and allow_reserved_for is None:
        return SPOT_OCCUPIED
    set_spot_occupant(con, spot_id, visit_id, reserved_move_id=None)
    return None


def vacate(con: sqlite3.Connection, spot_id: Optional[str], visit_id: str) -> None:
    if not spot_id:
        return
    spot = get_spot(con, spot_id)
    if spot is None:
        return
    if spot["occupant_visit_id"] == visit_id:
        set_spot_occupant(con, spot_id, None, reserved_move_id=spot["reserved_move_id"])


def reserve_dest(con: sqlite3.Connection, spot_id: str, move_id: str) -> Optional[str]:
    err = check_free(con, spot_id)
    if err:
        return err
    set_spot_occupant(con, spot_id, None, reserved_move_id=move_id)
    return None


def clear_reservation(con: sqlite3.Connection, spot_id: Optional[str], move_id: str) -> None:
    if not spot_id:
        return
    spot = get_spot(con, spot_id)
    if spot is None:
        return
    if spot["reserved_move_id"] == move_id:
        set_spot_occupant(con, spot_id, spot["occupant_visit_id"], reserved_move_id=None)


def check_free(con: sqlite3.Connection, spot_id: str) -> Optional[str]:
    spot = get_spot(con, spot_id)
    if spot is None:
        return SPOT_MISSING
    if spot["occupant_visit_id"] or spot["reserved_move_id"]:
        return SPOT_OCCUPIED
    return None
