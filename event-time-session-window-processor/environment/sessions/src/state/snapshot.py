from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.records import OpenSession
from src.state.atomic import atomic_write_json
from src.state.consistency import session_identity_ok
from src.time.watermark import comparison_watermark, raw_watermark


class ProcessorState:
    def __init__(self) -> None:
        self.max_observed_event_time_ms: int | None = None
        self.next_seq: int = 1
        self.sessions: dict[tuple[str, str], OpenSession] = {}

    def comparison_w(self, allowed_lateness_ms: int) -> int | None:
        return comparison_watermark(self.max_observed_event_time_ms, allowed_lateness_ms)

    def raw_w(self, allowed_lateness_ms: int) -> int | None:
        return raw_watermark(self.max_observed_event_time_ms, allowed_lateness_ms)

    def snapshot_dict(self) -> dict[str, Any]:
        ordered = sorted(
            self.sessions.values(),
            key=lambda sess: (sess.tenant_id, sess.user_id, sess.start_ms),
        )
        return {
            "max_observed_event_time_ms": self.max_observed_event_time_ms,
            "sessions": [sess.to_dict() for sess in ordered],
        }


def save_open_sessions(path: Path, state: ProcessorState) -> None:
    atomic_write_json(path, state.snapshot_dict())


def _load_max_observed(raw: dict[str, Any]) -> int | None:
    value = raw.get("max_observed_event_time_ms")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return int(value)


def _load_one_session(item: Any) -> OpenSession | None:
    if not isinstance(item, dict):
        return None
    required = ("tenant_id", "user_id", "start_ms", "last_event_time_ms", "event_ids")
    if any(key not in item for key in required):
        return None
    try:
        sess = OpenSession.from_dict(item)
    except (KeyError, TypeError, ValueError):
        return None
    if sess.last_event_time_ms < sess.start_ms:
        return None
    if not session_identity_ok(sess):
        return None
    return sess


def load_open_sessions(path: Path, state: ProcessorState) -> None:
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(raw, dict):
        return
    loaded_max = _load_max_observed(raw)
    if loaded_max is not None:
        if state.max_observed_event_time_ms is None:
            state.max_observed_event_time_ms = loaded_max
        else:
            state.max_observed_event_time_ms = max(state.max_observed_event_time_ms, loaded_max)
    for item in raw.get("sessions") or []:
        sess = _load_one_session(item)
        if sess is None:
            continue
        state.sessions[(sess.tenant_id, sess.user_id)] = sess
