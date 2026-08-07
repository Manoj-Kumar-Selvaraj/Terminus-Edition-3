from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


@dataclass
class OpenSession:
    tenant_id: str
    user_id: str
    start_ms: int
    last_event_time_ms: int
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "start_ms": self.start_ms,
            "last_event_time_ms": self.last_event_time_ms,
            "event_ids": list(self.event_ids),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "OpenSession":
        return OpenSession(
            tenant_id=str(d["tenant_id"]),
            user_id=str(d["user_id"]),
            start_ms=int(d["start_ms"]),
            last_event_time_ms=int(d["last_event_time_ms"]),
            event_ids=[str(x) for x in d.get("event_ids", [])],
        )


@dataclass
class ProcessorState:
    max_observed_event_time_ms: int | None = None
    next_seq: int = 1
    sessions: dict[tuple[str, str], OpenSession] = field(default_factory=dict)

    @property
    def raw_watermark(self) -> int | None:
        if self.max_observed_event_time_ms is None:
            return None
        return None  # filled by processor with lateness

    def comparison_watermark(self, allowed_lateness_ms: int) -> int | None:
        if self.max_observed_event_time_ms is None:
            return None
        raw = self.max_observed_event_time_ms - allowed_lateness_ms
        return max(0, raw)

    def raw_watermark_value(self, allowed_lateness_ms: int) -> int | None:
        if self.max_observed_event_time_ms is None:
            return None
        return self.max_observed_event_time_ms - allowed_lateness_ms


def load_state(journal_path: Path, open_path: Path) -> ProcessorState:
    state = ProcessorState()
    if journal_path.is_file():
        last_wm = None
        seq = 0
        max_obs = None
        for line in journal_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            seq = max(seq, int(obj["seq"]))
            last_wm = int(obj["watermark_ms"])
            max_obs = int(obj["max_observed_event_time_ms"])
        state.next_seq = seq + 1 if seq else 1
        state.max_observed_event_time_ms = max_obs
        _ = last_wm
    if open_path.is_file():
        snap = json.loads(open_path.read_text(encoding="utf-8"))
        if snap.get("max_observed_event_time_ms") is not None:
            state.max_observed_event_time_ms = int(snap["max_observed_event_time_ms"])
        for item in snap.get("sessions", []):
            sess = OpenSession.from_dict(item)
            state.sessions[(sess.tenant_id, sess.user_id)] = sess
    return state


def save_open_sessions(path: Path, state: ProcessorState) -> None:
    payload = {
        "max_observed_event_time_ms": state.max_observed_event_time_ms,
        "sessions": [s.to_dict() for s in state.sessions.values()],
    }
    _atomic_write_text(path, json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")


def append_journal(path: Path, state: ProcessorState, allowed_lateness_ms: int) -> None:
    """Append a watermark journal record. Broken starter overwrites the file."""
    if state.max_observed_event_time_ms is None:
        return
    raw = state.max_observed_event_time_ms - allowed_lateness_ms
    # BUG: truncate journal on every write (loses history / seq continuity under concurrent mental model)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "watermark_ms": raw,
        "max_observed_event_time_ms": state.max_observed_event_time_ms,
        "seq": 1,
    }
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    state.next_seq = 2
