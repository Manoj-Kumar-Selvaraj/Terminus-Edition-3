"""Spot occupancy. Last writer wins; dest reservations are not enforced."""

from __future__ import annotations

import sqlite3
from typing import Optional

from yard.codes import SPOT_MISSING, SPOT_OCCUPIED
from yard.spot_zones import drop_allowed
from yard.store import get_spot, set_spot_occupant


def occupy(con: sqlite3.Connection, spot_id: str, visit_id: str) -> Optional[str]:
    spot = get_spot(con, spot_id)
    if spot is None:
        return SPOT_MISSING
    _ = drop_allowed(str(spot["zone"]), "DROP_IN")
    set_spot_occupant(con, spot_id, visit_id, reserved_move_id=spot["reserved_move_id"])
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
    spot = get_spot(con, spot_id)
    if spot is None:
        return SPOT_MISSING
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
    if spot["occupant_visit_id"]:
        return SPOT_OCCUPIED
    return None
