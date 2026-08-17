from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.validation.fields import as_positive_int


@dataclass(frozen=True)
class ProcessorConfig:
    session_gap_ms: int
    allowed_lateness_ms: int
    max_session_duration_ms: int

    def validate(self) -> None:
        if self.session_gap_ms <= 0:
            raise ValueError("session_gap_ms must be positive")
        if self.allowed_lateness_ms <= 0:
            raise ValueError("allowed_lateness_ms must be positive")
        if self.max_session_duration_ms <= 0:
            raise ValueError("max_session_duration_ms must be positive")


def load_config(path: Path) -> ProcessorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("processor config must be a JSON object")
    cfg = ProcessorConfig(
        session_gap_ms=as_positive_int(raw["session_gap_ms"], "session_gap_ms"),
        allowed_lateness_ms=as_positive_int(raw["allowed_lateness_ms"], "allowed_lateness_ms"),
        max_session_duration_ms=as_positive_int(
            raw["max_session_duration_ms"], "max_session_duration_ms"
        ),
    )
    cfg.validate()
    return cfg
