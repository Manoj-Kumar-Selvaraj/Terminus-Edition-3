from __future__ import annotations

from src.config import ProcessorConfig
from src.records import OpenSession
from src.windows.operator import IdleClosePlanner


def watermark_close_candidates(
    sessions: dict[tuple[str, str], OpenSession],
    cfg: ProcessorConfig,
    comparison_w: int,
) -> list[tuple[tuple[str, str], OpenSession, int]]:
    planner = IdleClosePlanner(cfg)
    return planner.plan(sessions, comparison_w)
