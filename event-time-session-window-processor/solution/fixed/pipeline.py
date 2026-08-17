from __future__ import annotations

from pathlib import Path

from src.config import ProcessorConfig
from src.engine.emit import emit_closed_session
from src.engine.identity import CloseLog
from src.engine.session_step import apply_classified_event
from src.late.classify import classify_lateness
from src.metrics.counters import RunCounters
from src.records import Event
from src.runtime.checkpoint import append_watermark, save_open
from src.runtime.store import SessionStore
from src.runtime.watermark_track import WatermarkTrack
from src.state.snapshot import ProcessorState
from src.tenancy.directory import TenantDirectory
from src.tenancy.policy import bind_config
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
    directory: TenantDirectory | None = None,
) -> None:
    directory = directory or TenantDirectory.load()
    store = SessionStore()
    store.load_from(state.sessions)
    track = WatermarkTrack()
    track.sync_from(state.max_observed_event_time_ms)
    close_log = CloseLog()
    for idx, ev in enumerate(events):
        counters.observed += 1
        W = track.peek_comparison(cfg.allowed_lateness_ms)
        cfg_eff = bind_config(cfg, directory, ev.tenant_id)
        open_sess = store.open_for_event(ev)
        kind = classify_lateness(ev, open_sess, W, cfg_eff)
        directory.observe(ev, kind)
        apply_classified_event(
            kind,
            ev,
            open_sess,
            cfg_eff,
            W,
            store,
            idx,
            use_arrival_gap,
            sessions_out,
            late_out,
            counters,
            close_log,
        )
        track.record(ev.event_time_ms)
        state.max_observed_event_time_ms = track.max_observed_event_time_ms
        append_watermark(journal_path, state, cfg.allowed_lateness_ms)
        W2 = track.peek_comparison(cfg.allowed_lateness_ms)
        if W2 is not None:
            live = store.as_dict()
            for ckey, sess, end in watermark_close_candidates(live, cfg, W2, directory):
                emit_closed_session(sessions_out, sess, end, counters, close_log)
                store.pop_key(ckey)
        state.sessions = store.as_dict()
        save_open(open_path, state)
