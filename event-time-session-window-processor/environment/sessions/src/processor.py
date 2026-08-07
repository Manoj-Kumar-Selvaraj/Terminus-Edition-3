from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TextIO

from .config import ProcessorConfig
from .state import OpenSession, ProcessorState, append_journal, save_open_sessions


@dataclass
class Event:
    event_id: str
    tenant_id: str
    user_id: str
    event_time_ms: int
    payload: str
    line_no: int


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, separators=(",", ":"), sort_keys=True) + "\n")


def parse_event(line: str, line_no: int) -> tuple[Event | None, dict[str, Any] | None]:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None, {
            "code": "REJECT_MALFORMED",
            "event_id": None,
            "detail": "invalid json",
            "line_no": line_no,
        }
    if not isinstance(obj, dict):
        return None, {
            "code": "REJECT_MALFORMED",
            "event_id": None,
            "detail": "not an object",
            "line_no": line_no,
        }
    eid = obj.get("event_id")
    try:
        event_id = str(obj["event_id"])
        tenant_id = str(obj["tenant_id"])
        user_id = str(obj["user_id"])
        event_time_ms = int(obj["event_time_ms"])
        payload = str(obj["payload"])
    except (KeyError, TypeError, ValueError) as exc:
        return None, {
            "code": "REJECT_MALFORMED",
            "event_id": eid if isinstance(eid, str) else None,
            "detail": str(exc),
            "line_no": line_no,
        }
    if not event_id or not tenant_id or not user_id:
        return None, {
            "code": "REJECT_MALFORMED",
            "event_id": event_id or None,
            "detail": "empty identifier",
            "line_no": line_no,
        }
    if event_time_ms < 0:
        return None, {
            "code": "REJECT_MALFORMED",
            "event_id": event_id,
            "detail": "negative event_time_ms",
            "line_no": line_no,
        }
    return Event(event_id, tenant_id, user_id, event_time_ms, payload, line_no), None


def _session_key(ev: Event) -> tuple[str, str]:
    # BUG: ignore tenant_id — merges tenants that share user_id
    return ("*", ev.user_id)


def _close_session(
    sessions_out: Path,
    sess: OpenSession,
    end_ms: int,
) -> None:
    rec = {
        "tenant_id": sess.tenant_id,
        "user_id": sess.user_id,
        "start_ms": sess.start_ms,
        "end_ms": end_ms,
        "event_ids": list(sess.event_ids),
        "event_count": len(sess.event_ids),
    }
    _append_jsonl(sessions_out, rec)


def _watermark_close(
    state: ProcessorState,
    cfg: ProcessorConfig,
    sessions_out: Path,
    W: int,
) -> None:
    to_close: list[tuple[tuple[str, str], OpenSession, int]] = []
    for key, sess in list(state.sessions.items()):
        end_ms = sess.last_event_time_ms + cfg.session_gap_ms
        if end_ms <= W:
            to_close.append((key, sess, end_ms))
    for key, sess, end_ms in to_close:
        _close_session(sessions_out, sess, end_ms)
        del state.sessions[key]


def process_events(
    events: Iterable[Event],
    cfg: ProcessorConfig,
    state: ProcessorState,
    sessions_out: Path,
    late_out: Path,
    rejects_out: Path,
    journal_path: Path,
    open_path: Path,
    arrival_index_for_gap: bool = True,
) -> None:
    """Broken processor: processing-time gaps, watermark-before-late, tenant merge."""
    for idx, ev in enumerate(events):
        # BUG: advance watermark / max_observed BEFORE lateness decision
        prev_max = state.max_observed_event_time_ms
        if state.max_observed_event_time_ms is None:
            state.max_observed_event_time_ms = ev.event_time_ms
        else:
            state.max_observed_event_time_ms = max(state.max_observed_event_time_ms, ev.event_time_ms)
        W = state.comparison_watermark(cfg.allowed_lateness_ms)
        assert W is not None

        key = _session_key(ev)
        open_sess = state.sessions.get(key)

        if ev.event_time_ms < W:
            if (
                open_sess is not None
                and ev.event_time_ms >= open_sess.start_ms
                and ev.event_time_ms < open_sess.last_event_time_ms + cfg.session_gap_ms
            ):
                open_sess.event_ids.append(ev.event_id)
                if ev.event_time_ms > open_sess.last_event_time_ms:
                    open_sess.last_event_time_ms = ev.event_time_ms
            else:
                _append_jsonl(
                    late_out,
                    {
                        "event_id": ev.event_id,
                        "tenant_id": ev.tenant_id,
                        "user_id": ev.user_id,
                        "event_time_ms": ev.event_time_ms,
                        "watermark_ms": W,
                        "reason": "TOO_LATE",
                    },
                )
        else:
            # BUG: gap decision uses arrival index scaled as fake "processing time"
            if arrival_index_for_gap:
                synthetic = idx * 1000
                gap_left = open_sess.last_event_time_ms if open_sess else 0
                gap_trigger = synthetic >= gap_left + cfg.session_gap_ms if open_sess else False
            else:
                gap_trigger = (
                    open_sess is not None
                    and ev.event_time_ms >= open_sess.last_event_time_ms + cfg.session_gap_ms
                )

            if open_sess is not None:
                duration_exceeded = ev.event_time_ms - open_sess.start_ms > cfg.max_session_duration_ms
                if gap_trigger:
                    end_ms = open_sess.last_event_time_ms + cfg.session_gap_ms
                    _close_session(sessions_out, open_sess, end_ms)
                    # BUG: leave old session in map briefly then overwrite — also duplicate-prone on retry
                    del state.sessions[key]
                    open_sess = None
                elif duration_exceeded:
                    end_ms = open_sess.start_ms + cfg.max_session_duration_ms
                    _close_session(sessions_out, open_sess, end_ms)
                    del state.sessions[key]
                    open_sess = None

            if open_sess is None:
                open_sess = OpenSession(
                    tenant_id=ev.tenant_id,
                    user_id=ev.user_id,
                    start_ms=ev.event_time_ms,
                    last_event_time_ms=ev.event_time_ms,
                    event_ids=[ev.event_id],
                )
                state.sessions[key] = open_sess
            else:
                open_sess.event_ids.append(ev.event_id)
                if ev.event_time_ms > open_sess.last_event_time_ms:
                    open_sess.last_event_time_ms = ev.event_time_ms

        append_journal(journal_path, state, cfg.allowed_lateness_ms)
        W2 = state.comparison_watermark(cfg.allowed_lateness_ms)
        if W2 is not None:
            _watermark_close(state, cfg, sessions_out, W2)
        save_open_sessions(open_path, state)
        _ = prev_max


def sort_for_input(events: list[Event]) -> list[Event]:
    # Stable groups by event_time then (tenant, user, event_id) — correct for --input
    return sorted(events, key=lambda e: (e.event_time_ms, e.tenant_id, e.user_id, e.event_id))


def read_events(path: Path) -> tuple[list[Event], list[dict[str, Any]]]:
    events: list[Event] = []
    rejects: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        ev, rej = parse_event(line, line_no)
        if rej:
            rejects.append(rej)
        elif ev:
            events.append(ev)
    return events, rejects
