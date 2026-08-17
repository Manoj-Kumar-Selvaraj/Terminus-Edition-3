from __future__ import annotations

from typing import Any


def as_nonempty_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} type {type(value).__name__}")
    if not value:
        raise ValueError(f"{field} empty")
    if value.strip() != value:
        raise ValueError(f"{field} has surrounding whitespace")
    if not value.strip():
        raise ValueError(f"{field} empty")
    return value


def as_event_time(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("event_time_ms type")
    if value < 0:
        raise ValueError("negative event_time_ms")
    return int(value)


def as_payload(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("payload type")
    return value


def event_id_from_obj(obj: dict[str, Any]) -> str | None:
    eid = obj.get("event_id")
    return eid if isinstance(eid, str) else None


def as_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} type")
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return int(value)
