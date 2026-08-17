from __future__ import annotations

from pathlib import Path

from src.runtime.journal_codec import encode_journal_record, last_journal_values
from src.state.snapshot import ProcessorState


def append_journal(path: Path, state: ProcessorState, allowed_lateness_ms: int) -> None:
    if state.max_observed_event_time_ms is None:
        return
    raw = state.max_observed_event_time_ms - allowed_lateness_ms
    path.parent.mkdir(parents=True, exist_ok=True)
    seq = int(state.next_seq)
    line = encode_journal_record(raw, state.max_observed_event_time_ms, seq)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    state.next_seq = seq + 1


def load_journal(path: Path, state: ProcessorState) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    last = last_journal_values(text)
    if last is None:
        return
    seq, _wm, max_obs = last
    state.next_seq = int(seq) + 1
    state.max_observed_event_time_ms = int(max_obs)
