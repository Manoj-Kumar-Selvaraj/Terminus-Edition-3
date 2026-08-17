from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.records import Event


def tenant_histogram(events: Iterable[Event]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for ev in events:
        counts[ev.tenant_id] += 1
    return dict(sorted(counts.items()))


def user_histogram(events: Iterable[Event], *, limit: int = 50) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for ev in events:
        counts[f"{ev.tenant_id}/{ev.user_id}"] += 1
    top = counts.most_common(int(limit))
    return dict(top)


def time_span(events: Iterable[Event]) -> dict[str, Any]:
    min_t: int | None = None
    max_t: int | None = None
    n = 0
    for ev in events:
        n += 1
        min_t = ev.event_time_ms if min_t is None else min(min_t, ev.event_time_ms)
        max_t = ev.event_time_ms if max_t is None else max(max_t, ev.event_time_ms)
    return {"count": n, "min_event_time_ms": min_t, "max_event_time_ms": max_t}
