"""ISO-8601 helpers using configured yard timezone, including DST."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

UTC = timezone.utc


def parse_instant(value: str) -> datetime:
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_instant(value: datetime) -> str:
    utc = value.astimezone(UTC).replace(microsecond=0)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def to_local(value: datetime, tz_name: str) -> datetime:
    return value.astimezone(zone(tz_name))


def minutes_between(start: datetime, end: datetime) -> float:
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 60.0


def add_minutes(value: datetime, minutes: int) -> datetime:
    return value.astimezone(UTC) + timedelta(minutes=minutes)


def whole_minutes(value: float) -> int:
    if value <= 0:
        return 0
    return int(value)


def optional_parse(value: Optional[str]) -> Optional[datetime]:
    if value is None or value == "":
        return None
    return parse_instant(value)
