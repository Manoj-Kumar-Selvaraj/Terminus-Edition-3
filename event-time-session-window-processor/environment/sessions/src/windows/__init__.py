from __future__ import annotations

from src.windows.close import watermark_close_candidates
from src.windows.diagnostics import (
    describe_open_session,
    eligible_for_watermark_close,
    watermark_close_end,
)
from src.windows.interval import (
    adjacent_ok,
    closed_interval_valid,
    half_open_contains,
    intervals_overlap,
)
from src.windows.rules import duration_exceeded, gap_exceeded, should_close_for_on_time

__all__ = [
    "adjacent_ok",
    "closed_interval_valid",
    "describe_open_session",
    "duration_exceeded",
    "eligible_for_watermark_close",
    "gap_exceeded",
    "half_open_contains",
    "intervals_overlap",
    "should_close_for_on_time",
    "watermark_close_candidates",
    "watermark_close_end",
]
