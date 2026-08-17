"""Spot zone compatibility used at gate-in and dispatch."""

from __future__ import annotations

from typing import Optional

from yard.codes import LIVE_TYPES, ZONES


def zone_for_visit_type(visit_type: str, door_named: bool) -> tuple[str, ...]:
    if visit_type in LIVE_TYPES and door_named:
        return ("DOCK_APRON",)
    if visit_type == "DROP_IN":
        return ("DROP_LOT", "STAGING")
    if visit_type in {"EMPTY_OUT", "LOADED_PICKUP"}:
        return ("DROP_LOT", "STAGING", "DOCK_APRON")
    if visit_type in LIVE_TYPES:
        return ("DOCK_APRON", "STAGING")
    return ZONES


def drop_allowed(zone: str, visit_type: str) -> bool:
    allowed = zone_for_visit_type(visit_type, zone == "DOCK_APRON")
    return zone in allowed


def live_apron_required(visit_type: str, door_id: Optional[str]) -> bool:
    return visit_type in LIVE_TYPES and bool(door_id)


def chassis_stack_only(zone: str) -> bool:
    return zone == "CHASSIS_STACK"


def can_stage(zone: str) -> bool:
    return zone in {"STAGING", "DROP_LOT"}
