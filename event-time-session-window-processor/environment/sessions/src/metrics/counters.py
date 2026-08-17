from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.state.atomic import atomic_write_json
from src.paths import METRICS_PATH


@dataclass
class RunCounters:
    observed: int = 0
    on_time: int = 0
    late_allowed: int = 0
    too_late: int = 0
    rejected: int = 0
    closed: int = 0
    source_path: str = ""
    feed_mode: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "observed": self.observed,
            "on_time": self.on_time,
            "late_allowed": self.late_allowed,
            "too_late": self.too_late,
            "rejected": self.rejected,
            "closed": self.closed,
            "source_path": self.source_path,
            "feed_mode": self.feed_mode,
        }

    def persist(self, path: Path | None = None) -> None:
        atomic_write_json(path or METRICS_PATH, self.as_dict())


def empty_counters() -> RunCounters:
    return RunCounters()
