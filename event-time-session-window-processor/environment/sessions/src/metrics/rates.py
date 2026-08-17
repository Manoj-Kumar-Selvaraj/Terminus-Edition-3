from __future__ import annotations

from src.metrics.counters import RunCounters


def classify_rate(counters: RunCounters) -> dict[str, float]:
    observed = max(int(counters.observed), 1)
    return {
        "on_time": counters.on_time / observed,
        "late_allowed": counters.late_allowed / observed,
        "too_late": counters.too_late / observed,
        "rejected_over_observed": counters.rejected / observed,
        "closed_over_observed": counters.closed / observed,
    }


def totals(counters: RunCounters) -> int:
    return (
        counters.on_time
        + counters.late_allowed
        + counters.too_late
        + counters.rejected
    )
