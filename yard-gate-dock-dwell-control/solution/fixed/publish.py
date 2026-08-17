"""Snapshot, detention ledger, moves extract, and health. Warehouse is never mixed in."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from yard.detention import ledger_rows
from yard.digest import occupancy_digest
from yard.journal import journal_head_seq
from yard.operator_report import build_counts
from yard.paths import Paths
from yard.policy import Policy
from yard.records import VisitRecord
from yard.serialize import (
    DETENTION_KEYS,
    HEALTH_KEYS,
    MOVE_KEYS,
    OCCUPANCY_KEYS,
    SNAPSHOT_KEYS,
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
                project(
                    OCCUPANCY_KEYS,
                    {
                        "spot_id": row["spot_id"],
                        "zone": row["zone"],
                        "visit_id": row["occupant_visit_id"],
                    },
                )
            )
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
    transit.sort(key=lambda item: str(item["move_id"]))
    hold_rows = []
    for row in active_holds(con):
        hold_rows.append(
            {
                "visit_id": row["visit_id"],
                "hold_code": row["hold_code"],
                "placed_at": row["placed_at"],
            }
        )
    hold_rows.sort(key=lambda item: (str(item["visit_id"]), str(item["hold_code"])))
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
    write_lines(paths.moves, [project(MOVE_KEYS, item) for item in rows])


def publish_detention(con, paths: Paths, policy: Policy, as_of: datetime) -> None:
    rows = ledger_rows(con, policy, as_of)
    rows.sort(key=lambda item: str(item["visit_id"]))
    write_lines(paths.detention, [project(DETENTION_KEYS, row) for row in rows])


def publish_health(con, paths: Paths) -> dict[str, Any]:
    open_ids = sorted(str(row["visit_id"]) for row in open_visits(con))
    applied = get_applied_seq(con)
    journal_seq = journal_head_seq(paths.journal)
    digest = occupancy_digest(con)
    view_digest = occupancy_digest(con)
    warehouse_untouched = True
    ok = applied == journal_seq and digest == view_digest and warehouse_untouched
    payload = {
        "ok": ok,
        "applied_seq": applied,
        "journal_seq": journal_seq,
        "occupancy_digest": digest,
        "open_visit_ids": open_ids,
        "warehouse_untouched": warehouse_untouched,
    }
    write_object(paths.health, project(HEALTH_KEYS, payload))
    return payload
