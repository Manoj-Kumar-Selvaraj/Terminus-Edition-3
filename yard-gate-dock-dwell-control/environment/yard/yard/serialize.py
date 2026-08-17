"""Stable JSON object field order for published artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


SNAPSHOT_KEYS = (
    "facility_id",
    "generated_at",
    "yard_tz",
    "as_of",
    "open_visits",
    "occupancy",
    "doors",
    "in_transit",
    "holds",
    "counts",
)

VISIT_KEYS = (
    "visit_id",
    "scac",
    "trailer_number",
    "visit_type",
    "equipment",
    "state",
    "spot_id",
    "door_id",
    "gate_in",
    "appointment_id",
    "seal",
)

OCCUPANCY_KEYS = ("spot_id", "zone", "visit_id")
DOOR_KEYS = ("door_id", "door_class", "visit_id")
TRANSIT_KEYS = ("move_id", "visit_id", "origin_spot_id", "dest_spot_id")
HOLD_KEYS = ("visit_id", "hold_code", "placed_at")
COUNT_KEYS = ("open_visits", "occupied_spots", "doors_occupied", "in_transit", "active_holds")
DETENTION_KEYS = (
    "visit_id",
    "scac",
    "visit_type",
    "clock_start",
    "free_minutes",
    "pause_minutes",
    "chargeable_minutes",
    "status",
)
MOVE_KEYS = ("move_id", "visit_id", "state", "origin_spot_id", "dest_spot_id", "seq")
HEALTH_KEYS = (
    "ok",
    "applied_seq",
    "journal_seq",
    "occupancy_digest",
    "open_visit_ids",
    "warehouse_untouched",
)
REJECT_KEYS = ("code", "event_id", "detail")


def project(keys: Iterable[str], row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys}


def dumps_object(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def dumps_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":")) + "\n"


def write_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_object(payload), encoding="utf-8")


def write_lines(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(dumps_line(row))
