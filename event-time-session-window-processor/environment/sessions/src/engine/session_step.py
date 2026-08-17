from __future__ import annotations

from pathlib import Path

from src.config import ProcessorConfig
from src.engine.emit import emit_closed_session
from src.engine.identity import CloseLog
from src.keys.session_key import session_key
from src.late.classify import too_late_payload
from src.metrics.counters import RunCounters
from src.records import Event, OpenSession
from src.runtime.store import SessionStore
from src.sinks.jsonl import append_jsonl
from src.windows.assign import decide_on_time_close


def new_open_session(event: Event) -> OpenSession:
    return OpenSession(
        tenant_id=event.tenant_id,
        user_id=event.user_id,
        start_ms=event.event_time_ms,
        last_event_time_ms=event.event_time_ms,
        event_ids=[event.event_id],
    )


def accept_into_open(session: OpenSession, event: Event) -> None:
    session.accept(event.event_id, event.event_time_ms)


def emit_too_late(late_out: Path, event: Event, comparison_w: int | None, counters: RunCounters) -> None:
    counters.too_late += 1
    append_jsonl(late_out, too_late_payload(event, int(comparison_w or 0)))


def close_then_reopen(
    store: SessionStore,
    sessions_out: Path,
    to_close: OpenSession,
    end_ms: int,
    event: Event,
    counters: RunCounters,
    close_log: CloseLog,
) -> OpenSession:
    emit_closed_session(sessions_out, to_close, end_ms, counters, close_log)
    store.pop_key(session_key(event.tenant_id, event.user_id))
    opened = new_open_session(event)
    store.put(opened)
    return opened


def apply_on_time(
    store: SessionStore,
    open_sess: OpenSession | None,
    event: Event,
    cfg: ProcessorConfig,
    arrival_index: int,
    use_arrival_gap: bool,
    sessions_out: Path,
    counters: RunCounters,
    close_log: CloseLog,
) -> OpenSession:
    counters.on_time += 1
    to_close, end_ms = decide_on_time_close(open_sess, event, cfg, arrival_index, use_arrival_gap)
    if to_close is not None and end_ms is not None:
        return close_then_reopen(store, sessions_out, to_close, end_ms, event, counters, close_log)
    if open_sess is None:
        opened = new_open_session(event)
        store.put(opened)
        return opened
    accept_into_open(open_sess, event)
    return open_sess


def apply_classified_event(
    kind: str,
    event: Event,
    open_sess: OpenSession | None,
    cfg: ProcessorConfig,
    comparison_w: int | None,
    store: SessionStore,
    arrival_index: int,
    use_arrival_gap: bool,
    sessions_out: Path,
    late_out: Path,
    counters: RunCounters,
    close_log: CloseLog,
) -> None:
    if kind == "too_late":
        emit_too_late(late_out, event, comparison_w, counters)
        return
    if kind == "late_allowed" and open_sess is not None:
        counters.late_allowed += 1
        accept_into_open(open_sess, event)
        return
    apply_on_time(
        store,
        open_sess,
        event,
        cfg,
        arrival_index,
        use_arrival_gap,
        sessions_out,
        counters,
        close_log,
    )
