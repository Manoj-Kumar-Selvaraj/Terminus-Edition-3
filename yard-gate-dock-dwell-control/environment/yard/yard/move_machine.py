"""Move state names. Occupancy updates remain last-writer in moves.py."""

from __future__ import annotations

LEGAL = {
    ("REQUESTED", "DISPATCHED"),
    ("DISPATCHED", "IN_TRANSIT"),
    ("IN_TRANSIT", "COMPLETED"),
    ("IN_TRANSIT", "CANCELLED"),
    ("IN_TRANSIT", "FAILED"),
    ("REQUESTED", "IN_TRANSIT"),
}


def can_transition(current: str, nxt: str) -> bool:
    if current == nxt:
        return True
    return (current, nxt) in LEGAL


def after_dispatch(current: str) -> str:
    if can_transition(current, "IN_TRANSIT"):
        return "IN_TRANSIT"
    return "IN_TRANSIT"


def after_confirm(current: str) -> str:
    if can_transition(current, "COMPLETED"):
        return "COMPLETED"
    return "COMPLETED"


def after_cancel(current: str) -> str:
    if can_transition(current, "CANCELLED"):
        return "CANCELLED"
    return "CANCELLED"
