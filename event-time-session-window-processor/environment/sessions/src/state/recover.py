from __future__ import annotations

from pathlib import Path

from src.state.journal import load_journal
from src.state.snapshot import ProcessorState, load_open_sessions


def load_state(journal_path: Path, open_path: Path) -> ProcessorState:
    state = ProcessorState()
    load_journal(journal_path, state)
    load_open_sessions(open_path, state)
    return state
