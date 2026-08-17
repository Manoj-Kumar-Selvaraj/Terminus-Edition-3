from __future__ import annotations

from typing import Any


def strip_unknown_nulls(obj: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in obj.items() if value is not None}


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def payload_preview(value: str, *, limit: int = 120) -> str:
    text = value.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def normalize_object(obj: dict[str, Any]) -> dict[str, Any]:
    out = strip_unknown_nulls(obj)
    for key in ("event_id", "tenant_id", "user_id"):
        if key in out and isinstance(out[key], str):
            out[key] = out[key]
    if "payload" in out and isinstance(out["payload"], str):
        out["_payload_preview"] = payload_preview(out["payload"])
    return out
