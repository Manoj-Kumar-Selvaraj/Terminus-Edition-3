from __future__ import annotations

from src.config import ProcessorConfig


def comparison_watermark(max_observed: int | None, allowed_lateness_ms: int) -> int | None:
    if max_observed is None:
        return None
    raw = int(max_observed) - int(allowed_lateness_ms)
    return max(0, raw)


def raw_watermark(max_observed: int | None, allowed_lateness_ms: int) -> int | None:
    if max_observed is None:
        return None
    return int(max_observed) - int(allowed_lateness_ms)


def observe(max_observed: int | None, event_time_ms: int) -> int:
    if max_observed is None:
        return int(event_time_ms)
    return max(int(max_observed), int(event_time_ms))


def is_late(event_time_ms: int, comparison_w: int | None) -> bool:
    if comparison_w is None:
        return False
    return int(event_time_ms) < int(comparison_w)


def watermark_from_config(max_observed: int | None, cfg: ProcessorConfig) -> tuple[int | None, int | None]:
    return (
        raw_watermark(max_observed, cfg.allowed_lateness_ms),
        comparison_watermark(max_observed, cfg.allowed_lateness_ms),
    )
