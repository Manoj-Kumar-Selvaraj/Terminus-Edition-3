from __future__ import annotations

from pathlib import Path

from src.runtime.journal_codec import (
    encode_journal_record,
    iter_journal_records,
    last_journal_values,
)
from src.state.snapshot import ProcessorState


def append_journal(path: Path, state: ProcessorState, allowed_lateness_ms: int) -> None:
    if state.max_observed_event_time_ms is None:
        return
    raw = state.max_observed_event_time_ms - allowed_lateness_ms
    path.parent.mkdir(parents=True, exist_ok=True)
    line = encode_journal_record(raw, state.max_observed_event_time_ms, 1)
    path.write_text(line + "\n", encoding="utf-8")
    state.next_seq = 2


def load_journal(path: Path, state: ProcessorState) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    last = last_journal_values(text)
    seq = 0
    max_obs = None
    for rec in iter_journal_records(text):
        seq = max(seq, int(rec["seq"]))
        max_obs = int(rec["max_observed_event_time_ms"])
    if last is not None:
        seq = max(seq, last[0])
        max_obs = last[2]
    if seq:
        state.next_seq = seq + 1
    if max_obs is not None:
        state.max_observed_event_time_ms = max_obs
