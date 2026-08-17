from __future__ import annotations

from src.config import ProcessorConfig
from src.records import Event, OpenSession
from src.time.event_clock import event_time_ms
from src.windows.rules import duration_exceeded, gap_exceeded


def same_session_identity(session: OpenSession, event: Event) -> bool:
    return session.tenant_id == event.tenant_id and session.user_id == event.user_id


def event_before_session_start(session: OpenSession, event: Event) -> bool:
    return int(event.event_time_ms) < int(session.start_ms)


def event_in_gap_window(session: OpenSession, event: Event, gap_ms: int) -> bool:
    if event_before_session_start(session, event):
        return False
    return not gap_exceeded(session, event.event_time_ms, gap_ms)


def event_would_exceed_duration(session: OpenSession, event: Event, max_duration_ms: int) -> bool:
    return duration_exceeded(session, event.event_time_ms, max_duration_ms)


def late_join_eligible(session: OpenSession | None, event: Event, cfg: ProcessorConfig) -> bool:
    """Late-but-allowed uses the open interval and gap window, not max duration."""
    if session is None:
        return False
    if not same_session_identity(session, event):
        return False
    if event_before_session_start(session, event):
        return False
    if not event_in_gap_window(session, event, cfg.session_gap_ms):
        return False
    return True


def on_time_requires_new_session(
    session: OpenSession | None, event: Event, cfg: ProcessorConfig
) -> str | None:
    if session is None:
        return "open"
    if event_would_exceed_duration(session, event, cfg.max_session_duration_ms):
        return "duration"
    if gap_exceeded(session, event.event_time_ms, cfg.session_gap_ms):
        return "gap"
    return None


def last_event_after_accept(session: OpenSession, event_time_ms: int) -> int:
    if int(event_time_ms) > int(session.last_event_time_ms):
        return int(event_time_ms)
    return int(session.last_event_time_ms)


def comparison_defined(comparison_w: int | None) -> bool:
    return comparison_w is not None


def event_behind_watermark(event: Event, comparison_w: int | None) -> bool:
    if not comparison_defined(comparison_w):
        return False
    return event_time_ms(event.event_time_ms) < int(comparison_w)
