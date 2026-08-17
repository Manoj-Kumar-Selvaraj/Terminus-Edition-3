from __future__ import annotations

from src.config import ProcessorConfig
from src.records import OpenSession
from src.windows.gap_clock import duration_deadline_ms, idle_beyond_watermark, watermark_idle_end
from src.windows.interval import duration_ms


def describe_open_session(session: OpenSession, cfg: ProcessorConfig) -> dict[str, int | str]:
    gap_end = watermark_idle_end(session, cfg)
    dur_end = duration_deadline_ms(session.start_ms, cfg.max_session_duration_ms)
    return {
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "start_ms": session.start_ms,
        "last_event_time_ms": session.last_event_time_ms,
        "event_count": len(session.event_ids),
        "gap_close_end_ms": gap_end,
        "duration_close_end_ms": dur_end,
        "open_span_ms": duration_ms(session.start_ms, session.last_event_time_ms + 1) - 1,
    }


def watermark_close_end(session: OpenSession, cfg: ProcessorConfig) -> int:
    return watermark_idle_end(session, cfg)


def eligible_for_watermark_close(session: OpenSession, cfg: ProcessorConfig, comparison_w: int) -> bool:
    return idle_beyond_watermark(session, cfg, comparison_w)
