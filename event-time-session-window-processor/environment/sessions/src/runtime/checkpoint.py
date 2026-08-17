from __future__ import annotations

from pathlib import Path

from src.config import ProcessorConfig
from src.state.journal import append_journal
from src.state.snapshot import ProcessorState, save_open_sessions


def append_watermark(
    journal_path: Path, state: ProcessorState, allowed_lateness_ms: int
) -> None:
    append_journal(journal_path, state, allowed_lateness_ms)


def save_open(open_path: Path, state: ProcessorState) -> None:
    save_open_sessions(open_path, state)


def persist_observation(
    journal_path: Path,
    open_path: Path,
    state: ProcessorState,
    allowed_lateness_ms: int,
) -> None:
    append_watermark(journal_path, state, allowed_lateness_ms)
    save_open(open_path, state)


def persist_observation_from_config(
    journal_path: Path,
    open_path: Path,
    state: ProcessorState,
    cfg: ProcessorConfig,
) -> None:
    persist_observation(journal_path, open_path, state, cfg.allowed_lateness_ms)
