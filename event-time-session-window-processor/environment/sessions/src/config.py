from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessorConfig:
    session_gap_ms: int
    allowed_lateness_ms: int
    max_session_duration_ms: int


def load_config(path: Path) -> ProcessorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    gap = int(raw["session_gap_ms"])
    late = int(raw["allowed_lateness_ms"])
    dur = int(raw["max_session_duration_ms"])
    if gap <= 0 or late <= 0 or dur <= 0:
        raise ValueError("processor config values must be positive")
    return ProcessorConfig(gap, late, dur)
