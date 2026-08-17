"""Door and spot catalog queries used by publish and gate."""

from __future__ import annotations

import sqlite3
from typing import Any

from yard.store import fetchall, fetchone


def list_doors(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for row in fetchall(con, "SELECT * FROM doors ORDER BY door_id"):
        rows.append(
            {
                "door_id": row["door_id"],
                "door_class": row["door_class"],
                "reefer_plug": int(row["reefer_plug"]),
                "live_capable": int(row["live_capable"]),
                "drop_capable": int(row["drop_capable"]),
                "allowed_equipment": row["allowed_equipment"],
            }
        )
    return rows


def list_spots(con: sqlite3.Connection, zone: str | None = None) -> list[dict[str, Any]]:
    if zone:
        raw = fetchall(con, "SELECT * FROM spots WHERE zone = ? ORDER BY spot_id", (zone,))
    else:
        raw = fetchall(con, "SELECT * FROM spots ORDER BY spot_id")
    return [
        {
            "spot_id": row["spot_id"],
            "zone": row["zone"],
            "door_id": row["door_id"],
            "occupant_visit_id": row["occupant_visit_id"],
            "reserved_move_id": row["reserved_move_id"],
        }
        for row in raw
    ]


def empty_spots(con: sqlite3.Connection, zone: str) -> list[str]:
    rows = fetchall(
        con,
        "SELECT spot_id FROM spots WHERE zone = ? AND occupant_visit_id IS NULL "
        "AND reserved_move_id IS NULL ORDER BY spot_id",
        (zone,),
    )
    return [str(row["spot_id"]) for row in rows]


def apron_for_door(con: sqlite3.Connection, door_id: str) -> str | None:
    row = fetchone(
        con,
        "SELECT spot_id FROM spots WHERE door_id = ? AND zone = 'DOCK_APRON'",
        (door_id,),
    )
    return None if row is None else str(row["spot_id"])


def occupied_door_ids(con: sqlite3.Connection) -> list[str]:
    rows = fetchall(
        con,
        "SELECT door_id FROM spots WHERE zone = 'DOCK_APRON' AND occupant_visit_id IS NOT NULL ORDER BY door_id",
    )
    return [str(row["door_id"]) for row in rows]


def chassis_free(con: sqlite3.Connection) -> list[str]:
    rows = fetchall(
        con,
        "SELECT chassis_id FROM chassis_units WHERE mounted_visit_id IS NULL ORDER BY chassis_id",
    )
    return [str(row["chassis_id"]) for row in rows]
