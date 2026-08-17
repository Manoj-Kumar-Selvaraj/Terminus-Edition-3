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


def empty_identifier_fields(obj: dict[str, Any]) -> list[str]:
    empty: list[str] = []
    for field in ("event_id", "tenant_id", "user_id"):
        value = obj.get(field)
        if isinstance(value, str) and value == "":
            empty.append(field)
    return empty


def whitespace_identifier_fields(obj: dict[str, Any]) -> list[str]:
    bad: list[str] = []
    for field in ("event_id", "tenant_id", "user_id"):
        value = obj.get(field)
        if isinstance(value, str) and value != value.strip():
            bad.append(field)
    return bad


def payload_is_present(obj: dict[str, Any]) -> bool:
    return "payload" in obj


def payload_type_ok(obj: dict[str, Any]) -> bool:
    if not payload_is_present(obj):
        return False
    return isinstance(obj["payload"], str)


def event_time_type_ok(obj: dict[str, Any]) -> bool:
    value = obj.get("event_time_ms")
    return isinstance(value, int) and not isinstance(value, bool)


def first_schema_reject_reason(obj: dict[str, Any]) -> str | None:
    missing = missing_required_fields(obj)
    if missing:
        return f"missing {missing[0]}"
    empty = empty_identifier_fields(obj)
    if empty:
        return f"{empty[0]} empty"
    whitespace = whitespace_identifier_fields(obj)
    if whitespace:
        return f"{whitespace[0]} has surrounding whitespace"
    type_err = first_type_error(obj)
    if type_err is not None:
        return type_err
    if not payload_type_ok(obj):
        return "payload type"
    if not event_time_type_ok(obj):
        return "event_time_ms type"
    return None
