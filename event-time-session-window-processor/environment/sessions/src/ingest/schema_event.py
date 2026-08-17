from __future__ import annotations

from typing import Any

REQUIRED_EVENT_FIELDS = ("event_id", "tenant_id", "user_id", "event_time_ms", "payload")
STRING_FIELDS = ("event_id", "tenant_id", "user_id", "payload")
INTEGER_FIELDS = ("event_time_ms",)


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def missing_required_fields(obj: dict[str, Any]) -> list[str]:
    return [name for name in REQUIRED_EVENT_FIELDS if name not in obj]


def field_type_error(field: str, value: Any) -> str | None:
    kind = json_type_name(value)
    if field in STRING_FIELDS and kind != "string":
        return f"{field} type {kind}"
    if field in INTEGER_FIELDS and kind != "integer":
        return f"{field} type {kind}"
    return None


def first_type_error(obj: dict[str, Any]) -> str | None:
    for field in REQUIRED_EVENT_FIELDS:
        if field not in obj:
            continue
        err = field_type_error(field, obj[field])
        if err is not None:
            return err
    return None
