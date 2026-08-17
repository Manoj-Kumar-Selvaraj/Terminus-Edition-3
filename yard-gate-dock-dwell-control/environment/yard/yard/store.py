"""Sqlite access, occupancy views, and derived-row helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from yard.paths import Paths


def connect(paths: Paths) -> sqlite3.Connection:
    paths.sqlite.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(paths.sqlite))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_schema(con: sqlite3.Connection, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    con.executescript(sql)
    con.commit()


def fetchone(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    return con.execute(sql, tuple(params)).fetchone()


def fetchall(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return list(con.execute(sql, tuple(params)).fetchall())


def scalar(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> Any:
    row = fetchone(con, sql, params)
    if row is None:
        return None
    return row[0]


def get_applied_seq(con: sqlite3.Connection) -> int:
    value = scalar(con, "SELECT last_applied_seq FROM applied WHERE id = 1")
    return int(value or 0)


def set_applied_seq(con: sqlite3.Connection, seq: int) -> None:
    con.execute("UPDATE applied SET last_applied_seq = ? WHERE id = 1", (int(seq),))


def get_visit(con: sqlite3.Connection, visit_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM visits WHERE visit_id = ?", (visit_id,))


def get_spot(con: sqlite3.Connection, spot_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM spots WHERE spot_id = ?", (spot_id,))


def get_door(con: sqlite3.Connection, door_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM doors WHERE door_id = ?", (door_id,))


def get_appointment(con: sqlite3.Connection, appointment_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))


def get_move(con: sqlite3.Connection, move_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM moves WHERE move_id = ?", (move_id,))


def get_chassis(con: sqlite3.Connection, chassis_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM chassis_units WHERE chassis_id = ?", (chassis_id,))


def open_visits(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return fetchall(
        con,
        "SELECT * FROM visits WHERE state IN ('ON_YARD','MOVING','DOCKED') ORDER BY visit_id",
    )


def occupancy_rows(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return fetchall(
        con,
        "SELECT spot_id, zone, occupant_visit_id, reserved_move_id FROM spots "
        "WHERE occupant_visit_id IS NOT NULL OR reserved_move_id IS NOT NULL "
        "ORDER BY spot_id",
    )


def active_holds(con: sqlite3.Connection, visit_id: Optional[str] = None) -> list[sqlite3.Row]:
    if visit_id is None:
        return fetchall(
            con,
            "SELECT * FROM holds WHERE active = 1 ORDER BY visit_id, hold_code",
        )
    return fetchall(
        con,
        "SELECT * FROM holds WHERE active = 1 AND visit_id = ? ORDER BY hold_code",
        (visit_id,),
    )


def in_transit_moves(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return fetchall(
        con,
        "SELECT * FROM moves WHERE state = 'IN_TRANSIT' ORDER BY move_id",
    )


def upsert_visit(con: sqlite3.Connection, fields: dict[str, Any]) -> None:
    columns = [
        "visit_id",
        "scac",
        "trailer_number",
        "visit_type",
        "equipment",
        "state",
        "spot_id",
        "door_id",
        "appointment_id",
        "gate_in",
        "gate_out",
        "seal",
        "on_ground",
        "chassis_id",
        "clock_start",
    ]
    values = [fields.get(name) for name in columns]
    placeholders = ",".join("?" for _ in columns)
    colsql = ",".join(columns)
    updates = ",".join(f"{name}=excluded.{name}" for name in columns if name != "visit_id")
    con.execute(
        f"INSERT INTO visits ({colsql}) VALUES ({placeholders}) ON CONFLICT(visit_id) DO UPDATE SET {updates}",
        values,
    )


def set_spot_occupant(
    con: sqlite3.Connection,
    spot_id: str,
    visit_id: Optional[str],
    reserved_move_id: Optional[str] = None,
) -> None:
    con.execute(
        "UPDATE spots SET occupant_visit_id = ?, reserved_move_id = ? WHERE spot_id = ?",
        (visit_id, reserved_move_id, spot_id),
    )


def insert_event(con: sqlite3.Connection, event_id: str, seq: int, verb: str, body: str, accepted_at: str) -> None:
    con.execute(
        "INSERT OR REPLACE INTO event_log(event_id, seq, verb, body, accepted_at) VALUES (?,?,?,?,?)",
        (event_id, seq, verb, body, accepted_at),
    )


def get_event(con: sqlite3.Connection, event_id: str) -> Optional[sqlite3.Row]:
    return fetchone(con, "SELECT * FROM event_log WHERE event_id = ?", (event_id,))


def max_event_seq(con: sqlite3.Connection) -> int:
    value = scalar(con, "SELECT COALESCE(MAX(seq), 0) FROM event_log")
    return int(value or 0)


def warehouse_connect(paths: Paths) -> Optional[sqlite3.Connection]:
    if not paths.warehouse.is_file():
        return None
    con = sqlite3.connect(str(paths.warehouse))
    con.row_factory = sqlite3.Row
    return con
