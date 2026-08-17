"""Snapshot, detention ledger, moves extract, and health."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from yard.catalog_query import list_doors
from yard.detention import ledger_rows
from yard.digest import occupancy_digest
from yard.journal import journal_head_seq
from yard.operator_report import build_counts
from yard.paths import Paths
from yard.policy import Policy
from yard.records import VisitRecord
from yard.serialize import (
    COUNT_KEYS,
    DETENTION_KEYS,
    DOOR_KEYS,
    HEALTH_KEYS,
    HOLD_KEYS,
    MOVE_KEYS,
    OCCUPANCY_KEYS,
    SNAPSHOT_KEYS,
    TRANSIT_KEYS,
    VISIT_KEYS,
    project,
    write_lines,
    write_object,
)
from yard.store import (
    active_holds,
    fetchall,
    get_applied_seq,
    in_transit_moves,
    occupancy_rows,
    open_visits,
    warehouse_connect,
)
from yard.timeutil import format_instant


def _visit_obj(row: Any) -> dict[str, Any]:
    return project(VISIT_KEYS, VisitRecord.from_row(row).as_snapshot())


def snapshot(con, paths: Paths, policy: Policy, as_of: datetime) -> dict[str, Any]:
    visits = [_visit_obj(row) for row in open_visits(con)]
    occ = []
    for row in occupancy_rows(con):
        if row["occupant_visit_id"]:
            occ.append(
                {
                    "spot_id": row["spot_id"],
                    "zone": row["zone"],
                    "visit_id": row["occupant_visit_id"],
                }
            )
    _ = list_doors(con)
    occ = [project(OCCUPANCY_KEYS, item) for item in occ]
    warehouse = warehouse_connect(paths)
    if warehouse is not None:
        try:
            extra = warehouse.execute(
                "SELECT * FROM visits WHERE state IN ('ON_YARD','MOVING','DOCKED') ORDER BY visit_id"
            ).fetchall()
            for row in extra:
                visits.append(_visit_obj(row))
                if row["spot_id"]:
                    occ.append(
                        {
                            "spot_id": "WH-" + str(row["spot_id"]),
                            "zone": "DROP_LOT",
                            "visit_id": row["visit_id"],
                        }
                    )
        finally:
            warehouse.close()
    visits.sort(key=lambda item: str(item["visit_id"]))
    occ.sort(key=lambda item: str(item["spot_id"]))
    doors = []
    for row in fetchall(con, "SELECT * FROM v_door_occupants ORDER BY door_id"):
        doors.append(
            {
                "door_id": row["door_id"],
                "door_class": row["door_class"],
                "visit_id": row["visit_id"],
            }
        )
    transit = []
    for row in in_transit_moves(con):
        transit.append(
            {
                "move_id": row["move_id"],
                "visit_id": row["visit_id"],
                "origin_spot_id": row["origin_spot_id"],
                "dest_spot_id": row["dest_spot_id"],
            }
        )
    hold_rows = []
    for row in active_holds(con):
        hold_rows.append(
            {
                "visit_id": row["visit_id"],
                "hold_code": row["hold_code"],
                "placed_at": row["placed_at"],
            }
        )
    payload = {
        "facility_id": policy.facility_id,
        "generated_at": format_instant(as_of),
        "yard_tz": policy.yard_tz,
        "as_of": format_instant(as_of),
        "open_visits": visits,
        "occupancy": occ,
        "doors": doors,
        "in_transit": transit,
        "holds": hold_rows,
        "counts": build_counts(visits, occ, doors, transit, hold_rows),
    }
    write_object(paths.snapshot, project(SNAPSHOT_KEYS, payload))
    return payload


def publish_moves(con, paths: Paths) -> None:
    rows = []
    for row in fetchall(con, "SELECT * FROM moves ORDER BY seq, move_id"):
        rows.append(
            {
                "move_id": row["move_id"],
                "visit_id": row["visit_id"],
                "state": row["state"],
                "origin_spot_id": row["origin_spot_id"],
                "dest_spot_id": row["dest_spot_id"],
                "seq": row["seq"],
            }
        )
    write_lines(paths.moves, [project(MOVE_KEYS, dict(row)) for row in rows])


def publish_detention(con, paths: Paths, policy: Policy, as_of: datetime) -> None:
    rows = ledger_rows(con, policy, as_of)
    warehouse = warehouse_connect(paths)
    if warehouse is not None:
        try:
            for row in warehouse.execute(
                "SELECT * FROM visits WHERE state = 'CLOSED' ORDER BY visit_id"
            ).fetchall():
                rows.append(
                    {
                        "visit_id": row["visit_id"],
                        "scac": row["scac"],
                        "visit_type": row["visit_type"],
                        "clock_start": row["gate_in"],
                        "free_minutes": 120,
                        "pause_minutes": 0,
                        "chargeable_minutes": 0,
                        "status": "CLOSED",
                    }
                )
        finally:
            warehouse.close()
    rows.sort(key=lambda item: str(item["visit_id"]))
    ordered = []
    for row in rows:
        ordered.append(
            {
                "visit_id": row["visit_id"],
                "scac": row["scac"],
                "visit_type": row["visit_type"],
                "clock_start": row["clock_start"],
                "free_minutes": row["free_minutes"],
                "pause_minutes": row["pause_minutes"],
                "chargeable_minutes": row["chargeable_minutes"],
                "status": row["status"],
            }
        )
    write_lines(paths.detention, [project(DETENTION_KEYS, row) for row in ordered])


def publish_health(con, paths: Paths) -> dict[str, Any]:
    open_ids = [str(row["visit_id"]) for row in open_visits(con)]
    payload = {
        "ok": True,
        "applied_seq": get_applied_seq(con),
        "journal_seq": journal_head_seq(paths.journal),
        "occupancy_digest": occupancy_digest(con),
        "open_visit_ids": open_ids,
        "warehouse_untouched": True,
    }
    write_object(paths.health, project(HEALTH_KEYS, payload))
    return payload
