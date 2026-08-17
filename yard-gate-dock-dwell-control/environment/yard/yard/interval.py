"""Pause-interval merge used by the detention ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from yard.timeutil import minutes_between


def merge_intervals(intervals: Sequence[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    cleaned = [(lo, hi) for lo, hi in intervals if hi > lo]
    if not cleaned:
        return []
    cleaned.sort(key=lambda item: item[0])
    merged = [cleaned[0]]
    for lo, hi in cleaned[1:]:
        last_lo, last_hi = merged[-1]
        if lo <= last_hi:
            merged[-1] = (last_lo, max(last_hi, hi))
        else:
            merged.append((lo, hi))
    return merged


def clip(interval: tuple[datetime, datetime], start: datetime, end: datetime) -> tuple[datetime, datetime] | None:
    lo = max(interval[0], start)
    hi = min(interval[1], end)
    if hi <= lo:
        return None
    return lo, hi


def covered_minutes(
    intervals: Iterable[tuple[datetime, datetime]],
    start: datetime,
    end: datetime,
) -> float:
    clipped: list[tuple[datetime, datetime]] = []
    for interval in intervals:
        piece = clip(interval, start, end)
        if piece is not None:
            clipped.append(piece)
    total = 0.0
    for lo, hi in merge_intervals(clipped):
        total += minutes_between(lo, hi)
    return total
