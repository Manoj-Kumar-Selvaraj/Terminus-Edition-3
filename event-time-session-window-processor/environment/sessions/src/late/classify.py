from __future__ import annotations

from src.config import ProcessorConfig
from src.errors import late_record
from src.records import Event, OpenSession
from src.time.watermark import is_late


def late_but_allowed(session: OpenSession | None, event: Event, cfg: ProcessorConfig) -> bool:
    if session is None:
        return False
    if event.event_time_ms < session.start_ms:
        return False
    return event.event_time_ms < session.last_event_time_ms + cfg.session_gap_ms


def classify_lateness(
    event: Event,
    session: OpenSession | None,
    comparison_w: int | None,
    cfg: ProcessorConfig,
) -> str:
    """Return 'on_time', 'late_allowed', or 'too_late'."""
    if not is_late(event.event_time_ms, comparison_w):
        return "on_time"
    if late_but_allowed(session, event, cfg):
        return "late_allowed"
    return "too_late"


def too_late_payload(event: Event, comparison_w: int) -> dict:
    return late_record(
        event.event_id,
        event.tenant_id,
        event.user_id,
        event.event_time_ms,
        comparison_w,
    )
