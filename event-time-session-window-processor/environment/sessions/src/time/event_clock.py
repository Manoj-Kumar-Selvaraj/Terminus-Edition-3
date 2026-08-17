from __future__ import annotations

"""Event-time helpers. Arrival index is never a substitute for event_time_ms."""


def event_time_ms(value: int) -> int:
    if value < 0:
        raise ValueError("event_time_ms must be >= 0")
    return int(value)


def arrival_is_not_event_time(arrival_index: int, event_time_ms_value: int) -> bool:
    return int(arrival_index) != int(event_time_ms_value)
