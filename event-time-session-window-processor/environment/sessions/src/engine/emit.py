from __future__ import annotations

from src.windows.close import watermark_close_candidates
from src.windows.diagnostics import describe_open_session
from src.windows.interval import closed_interval_valid
from src.config import ProcessorConfig
from src.engine.identity import CloseLog, ClosedIdentity
from src.errors import closed_session_record
from src.metrics.counters import RunCounters
from src.records import OpenSession
from src.sinks.jsonl import append_jsonl
from pathlib import Path


def emit_closed_session(
    sessions_out: Path,
    sess: OpenSession,
    end_ms: int,
    counters: RunCounters,
    close_log: CloseLog,
) -> bool:
    ident = ClosedIdentity(sess.tenant_id, sess.user_id, sess.start_ms, end_ms)
    if not close_log.should_emit(ident):
        return False
    if not closed_interval_valid(sess.start_ms, end_ms):
        return False
    append_jsonl(
        sessions_out,
        closed_session_record(sess.tenant_id, sess.user_id, sess.start_ms, end_ms, sess.event_ids),
    )
    counters.closed += 1
    return True


def describe_store(sessions: dict, cfg: ProcessorConfig) -> list[dict]:
    out = []
    for sess in sessions.values():
        out.append(describe_open_session(sess, cfg))
    return out


def pending_watermark_closes(sessions: dict, cfg: ProcessorConfig, comparison_w: int) -> int:
    return len(watermark_close_candidates(sessions, cfg, comparison_w))
