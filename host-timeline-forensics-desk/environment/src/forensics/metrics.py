"""Low-cardinality process metrics and bounded diagnostic events."""
from __future__ import annotations
from collections import Counter, deque
from threading import Lock
from time import monotonic
from typing import Any


class Metrics:
    ALLOWED_NAMES = {"collection_claimed", "collection_dispatched", "collection_failed", "event_applied", "event_rejected", "evidence_verified", "export_published", "lease_recovered"}
    ALLOWED_LABELS = {"source", "mode", "result", "component"}

    def __init__(self, max_errors: int = 1000):
        self._lock = Lock()
        self._counters: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()
        self._errors: deque[dict[str, Any]] = deque(maxlen=max(1, min(max_errors, 5000)))
        self._started = monotonic()

    def inc(self, name: str, amount: int = 1, **labels: str) -> None:
        if name not in self.ALLOWED_NAMES or amount < 0:
            return
        safe = tuple(sorted((key, str(value)[:48]) for key, value in labels.items() if key in self.ALLOWED_LABELS))
        with self._lock:
            self._counters[(name, safe)] += amount

    def error(self, code: str, message: str, *, component: str = "service") -> None:
        with self._lock:
            self._errors.append({"code": str(code)[:64], "message": str(message)[:240], "component": component[:48]})

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = [
                {"name": name, "labels": dict(labels), "value": value}
                for (name, labels), value in sorted(self._counters.items())
            ]
            errors = list(self._errors)
        return {"uptime_seconds": max(0, int(monotonic() - self._started)), "counters": counters, "recent_errors": errors}


metrics = Metrics()
