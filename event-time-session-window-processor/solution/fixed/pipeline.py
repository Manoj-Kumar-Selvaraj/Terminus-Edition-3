from __future__ import annotations

from pathlib import Path

from src.config import ProcessorConfig
from src.engine.emit import emit_closed_session
from src.engine.identity import CloseLog
from src.keys.session_key import session_key
from src.late.classify import classify_lateness, too_late_payload
from src.metrics.counters import RunCounters
from src.records import Event, OpenSession
from src.runtime.checkpoint import append_watermark, save_open
from src.runtime.store import SessionStore
from src.runtime.watermark_track import WatermarkTrack
from src.sinks.jsonl import append_jsonl
from src.state.snapshot import ProcessorState
from src.windows.assign import decide_on_time_close
from src.windows.close import watermark_close_candidates


def process_events(
    events: list[Event],
    cfg: ProcessorConfig,
    state: ProcessorState,
    sessions_out: Path,
    late_out: Path,
    journal_path: Path,
    open_path: Path,
    counters: RunCounters,
    use_arrival_gap: bool = False,
) -> None:
    store = SessionStore()
    store.load_from(state.sessions)
    track = WatermarkTrack()
    track.sync_from(state.max_observed_event_time_ms)
    close_log = CloseLog()
    for idx, ev in enumerate(events):
        counters.observed += 1
        W = track.peek_comparison(cfg.allowed_lateness_ms)
        open_sess = store.open_for_event(ev)
        kind = classify_lateness(ev, open_sess, W, cfg)
        key = session_key(ev.tenant_id, ev.user_id)
        if kind == "too_late":
            counters.too_late += 1
            append_jsonl(late_out, too_late_payload(ev, int(W or 0)))
        elif kind == "late_allowed" and open_sess is not None:
            counters.late_allowed += 1
            open_sess.accept(ev.event_id, ev.event_time_ms)
        else:
            counters.on_time += 1
            to_close, end_ms = decide_on_time_close(open_sess, ev, cfg, idx, use_arrival_gap)
            if to_close is not None and end_ms is not None:
                emit_closed_session(sessions_out, to_close, end_ms, counters, close_log)
                store.pop_key(key)
                open_sess = None
            if open_sess is None:
                open_sess = OpenSession(
                    tenant_id=ev.tenant_id,
                    user_id=ev.user_id,
                    start_ms=ev.event_time_ms,
                    last_event_time_ms=ev.event_time_ms,
                    event_ids=[ev.event_id],
                )
                store.put(open_sess)
            else:
                open_sess.accept(ev.event_id, ev.event_time_ms)
        track.record(ev.event_time_ms)
        state.max_observed_event_time_ms = track.max_observed_event_time_ms
        append_watermark(journal_path, state, cfg.allowed_lateness_ms)
        W2 = track.peek_comparison(cfg.allowed_lateness_ms)
        if W2 is not None:
            live = store.as_dict()
            for ckey, sess, end in watermark_close_candidates(live, cfg, W2):
                emit_closed_session(sessions_out, sess, end, counters, close_log)
                store.pop_key(ckey)
        state.sessions = store.as_dict()
        save_open(open_path, state)
