from __future__ import annotations

from src.config import ProcessorConfig
from src.records import OpenSession


def gap_deadline_ms(last_event_time_ms: int, gap_ms: int) -> int:
    return int(last_event_time_ms) + int(gap_ms)


def duration_deadline_ms(start_ms: int, max_duration_ms: int) -> int:
    return int(start_ms) + int(max_duration_ms)


def idle_deadline_ms(session: OpenSession, cfg: ProcessorConfig) -> int:
    return gap_deadline_ms(session.last_event_time_ms, cfg.session_gap_ms)


def idle_beyond_watermark(session: OpenSession, cfg: ProcessorConfig, comparison_w: int) -> bool:
    return idle_deadline_ms(session, cfg) <= int(comparison_w)


def event_crosses_gap(session: OpenSession, event_time_ms: int, gap_ms: int) -> bool:
    return int(event_time_ms) >= gap_deadline_ms(session.last_event_time_ms, gap_ms)


def event_crosses_duration(session: OpenSession, event_time_ms: int, max_duration_ms: int) -> bool:
    return int(event_time_ms) - int(session.start_ms) > int(max_duration_ms)


def close_end_for_reason(session: OpenSession, cfg: ProcessorConfig, reason: str) -> int:
    if reason == "duration":
        return duration_deadline_ms(session.start_ms, cfg.max_session_duration_ms)
    return idle_deadline_ms(session, cfg)


def watermark_idle_end(session: OpenSession, cfg: ProcessorConfig) -> int:
    return idle_deadline_ms(session, cfg)
