from __future__ import annotations

from src.config import ProcessorConfig
from src.records import OpenSession
from src.time.timers import EventTimeTimers


def watermark_close_candidates(
    sessions: dict[tuple[str, str], OpenSession],
    cfg: ProcessorConfig,
    comparison_w: int,
) -> list[tuple[tuple[str, str], OpenSession, int]]:
    timers = EventTimeTimers.from_config(cfg)
    return timers.sync_from_store(sessions, cfg, comparison_w)
