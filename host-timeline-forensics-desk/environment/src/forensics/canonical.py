"""Canonical identity, time, JSON, and digest helpers."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .errors import InvalidRequest

_CASE = re.compile(r"^[A-Z][A-Z0-9_-]{2,47}$")
_ENDPOINT = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,95}$")
_SOURCE = re.compile(r"^[a-z][a-z0-9_.:-]{1,95}$")


def canonical_value(value: Any) -> Any:
    """Convert supported values into a stable JSON-compatible representation."""
    if isinstance(value, datetime):
        return format_utc(value)
    if isinstance(value, dict):
        return {str(key): canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    if isinstance(value, set):
        return sorted(canonical_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "value"):
        return canonical_value(value.value)
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        try:
            dt = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        except (ValueError, TypeError) as exc:
            raise InvalidRequest("timestamp must be ISO-8601 with an offset") from exc
    if dt.tzinfo is None:
        raise InvalidRequest("timestamp must include a timezone offset")
    return dt.astimezone(timezone.utc)


def format_utc(value: str | datetime) -> str:
    return parse_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_case_id(value: str) -> str:
    result = value.strip().upper()
    if not _CASE.fullmatch(result):
        raise InvalidRequest("case_id is not a valid case identity")
    return result


def normalize_endpoint_id(value: str) -> str:
    """Normalize a solver-visible endpoint identifier before scoped lookup."""
    result = value.strip().upper()
    if not _ENDPOINT.fullmatch(result):
        raise InvalidRequest("endpoint_id is not a valid endpoint identity")
    return result


def normalize_source_id(value: str) -> str:
    result = value.strip().lower()
    if not _SOURCE.fullmatch(result):
        raise InvalidRequest("source_id is not a valid source identity")
    return result


def stable_key(namespace: str, *parts: str) -> str:
    payload = "\x1f".join([namespace, *(part.strip() for part in parts)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bounded_text(value: Any, limit: int = 512) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"
