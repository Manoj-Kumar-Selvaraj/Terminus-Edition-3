from __future__ import annotations

from src.config import ProcessorConfig
from src.records import Event, OpenSession


def gap_exceeded(session: OpenSession, event_time_ms: int, gap_ms: int) -> bool:
    return int(event_time_ms) >= int(session.last_event_time_ms) + int(gap_ms)


def duration_exceeded(session: OpenSession, event_time_ms: int, max_duration_ms: int) -> bool:
    return int(event_time_ms) - int(session.start_ms) > int(max_duration_ms)


def gap_close_end(session: OpenSession, gap_ms: int) -> int:
    return int(session.last_event_time_ms) + int(gap_ms)


def duration_close_end(session: OpenSession, max_duration_ms: int) -> int:
    return int(session.start_ms) + int(max_duration_ms)


def should_close_for_on_time(session: OpenSession, event: Event, cfg: ProcessorConfig) -> tuple[str | None, int]:
    if duration_exceeded(session, event.event_time_ms, cfg.max_session_duration_ms):
        return "duration", duration_close_end(session, cfg.max_session_duration_ms)
    if gap_exceeded(session, event.event_time_ms, cfg.session_gap_ms):
        return "gap", gap_close_end(session, cfg.session_gap_ms)
    return None, 0


def arrival_gap_exceeded(session: OpenSession, arrival_index: int, gap_ms: int) -> bool:
    synthetic = int(arrival_index) * 1000
    return synthetic >= int(session.last_event_time_ms) + int(gap_ms)
