from __future__ import annotations

from pathlib import Path

from src.sinks.jsonl import ensure_empty
from src.state.snapshot import ProcessorState, save_open_sessions


def apply_empty_check(sessions_out: Path, late_out: Path, open_path: Path, state: ProcessorState) -> None:
    ensure_empty(sessions_out)
    ensure_empty(late_out)
    save_open_sessions(open_path, state)
