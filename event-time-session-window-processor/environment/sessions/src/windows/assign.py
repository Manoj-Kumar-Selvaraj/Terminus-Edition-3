from __future__ import annotations

from src.config import ProcessorConfig
from src.records import Event, OpenSession
from src.windows.rules import arrival_gap_exceeded, duration_exceeded, duration_close_end, gap_close_end


def decide_on_time_close(
    session: OpenSession | None,
    event: Event,
    cfg: ProcessorConfig,
    arrival_index: int,
    use_arrival_gap: bool,
) -> tuple[OpenSession | None, int | None]:
    """Return (session_to_close, end_ms) or (None, None)."""
    if session is None:
        return None, None
    if duration_exceeded(session, event.event_time_ms, cfg.max_session_duration_ms):
        return session, duration_close_end(session, cfg.max_session_duration_ms)
    if use_arrival_gap:
        if arrival_gap_exceeded(session, arrival_index, cfg.session_gap_ms):
            return session, gap_close_end(session, cfg.session_gap_ms)
        return None, None
    if event.event_time_ms >= session.last_event_time_ms + cfg.session_gap_ms:
        return session, gap_close_end(session, cfg.session_gap_ms)
    return None, None
