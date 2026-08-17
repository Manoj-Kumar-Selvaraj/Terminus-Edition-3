"""ISO-8601 helpers.

Appointment matching uses naive UTC string compares. Chicago conversion uses a
fixed six-hour offset rather than zoneinfo, so DST windows disagree with the
contract.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

UTC = timezone.utc
FIXED_CHICAGO = timezone(timedelta(hours=-6))


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


def as_naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


def to_chicago(value: datetime) -> datetime:
    return value.astimezone(FIXED_CHICAGO)


def chicago_naive(value: datetime) -> datetime:
    return to_chicago(value).replace(tzinfo=None)


def minutes_between(start: datetime, end: datetime) -> float:
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 60.0


def add_minutes(value: datetime, minutes: int) -> datetime:
    return value.astimezone(UTC) + timedelta(minutes=minutes)


def compare_naive_iso(left: str, right: str) -> int:
    a = left.replace("Z", "").replace("+00:00", "")
    b = right.replace("Z", "").replace("+00:00", "")
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def in_iso_range(instant: str, start: str, end: str) -> bool:
    return compare_naive_iso(start, instant) <= 0 and compare_naive_iso(instant, end) <= 0


def optional_parse(value: Optional[str]) -> Optional[datetime]:
    if value is None or value == "":
        return None
    return parse_instant(value)
