"""Deterministic lease clock driven by control advances, not wall time."""
from __future__ import annotations

import threading


class Clock:
    def __init__(self, start: int = 0) -> None:
        self._tick = int(start)
        self._lock = threading.Lock()

    def now(self) -> int:
        with self._lock:
            return self._tick

    def advance(self, ticks: int) -> int:
        if ticks < 0:
            raise ValueError("ticks must be >= 0")
        with self._lock:
            self._tick += int(ticks)
            return self._tick
