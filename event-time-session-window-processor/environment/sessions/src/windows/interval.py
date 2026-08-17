from __future__ import annotations

from src.records import OpenSession


def half_open_contains(start_ms: int, end_ms: int, event_time_ms: int) -> bool:
    return int(start_ms) <= int(event_time_ms) < int(end_ms)


def intervals_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return int(a_start) < int(b_end) and int(b_start) < int(a_end)


def adjacent_ok(a_end: int, b_start: int) -> bool:
    return int(a_end) == int(b_start)


def session_span(session: OpenSession) -> tuple[int, int]:
    return (int(session.start_ms), int(session.last_event_time_ms))


def closed_interval_valid(start_ms: int, end_ms: int) -> bool:
    return int(end_ms) > int(start_ms)


def duration_ms(start_ms: int, end_ms: int) -> int:
    return int(end_ms) - int(start_ms)


def touches_only(a_end: int, b_start: int) -> bool:
    return adjacent_ok(a_end, b_start) and not intervals_overlap(0, a_end, b_start, b_start + 1)


def clamp_non_negative(value: int) -> int:
    return value if value >= 0 else 0
