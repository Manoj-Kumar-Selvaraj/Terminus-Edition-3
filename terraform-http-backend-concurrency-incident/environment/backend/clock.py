"""Broken starter clock: wall-time based (leases race / never align with control advance)."""
from __future__ import annotations

import threading
import time


class Clock:
    def __init__(self, start: int = 0) -> None:
        self._tick = int(start)
        self._lock = threading.Lock()
        # BUG: mixes wall time into lease decisions
        self._wall_origin = time.time()

    def now(self) -> int:
        with self._lock:
            # Ignore control advances for lease math.
            return int(time.time() - self._wall_origin)

    def advance(self, ticks: int) -> int:
        if ticks < 0:
            raise ValueError("ticks must be >= 0")
        with self._lock:
            self._tick += int(ticks)
            return self._tick
