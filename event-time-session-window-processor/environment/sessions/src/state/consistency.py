from __future__ import annotations

from typing import Any

from src.records import OpenSession
from src.windows.interval import closed_interval_valid


def session_identity_ok(session: OpenSession) -> bool:
    if not session.tenant_id or not session.user_id:
        return False
    if session.last_event_time_ms < session.start_ms:
        return False
    if not session.event_ids:
        return False
    return True


def snapshot_duplicates(sessions: list[OpenSession]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    dupes: list[tuple[str, str]] = []
    for sess in sessions:
        key = (sess.tenant_id, sess.user_id)
        if key in seen:
            dupes.append(key)
        seen.add(key)
    return dupes


def snapshot_interval_problems(sessions: list[OpenSession]) -> int:
    bad = 0
    for sess in sessions:
        if not closed_interval_valid(sess.start_ms, sess.last_event_time_ms + 1):
            bad += 1
    return bad


def snapshot_health(sessions: list[OpenSession], max_observed: int | None) -> dict[str, Any]:
    invalid = sum(0 if session_identity_ok(s) else 1 for s in sessions)
    dupes = snapshot_duplicates(sessions)
    interval_problems = snapshot_interval_problems(sessions)
    covers = True
    if max_observed is not None:
        covers = all(s.last_event_time_ms <= max_observed for s in sessions)
    ok = invalid == 0 and not dupes and interval_problems == 0 and covers
    return {
        "open_sessions": len(sessions),
        "invalid_identities": invalid,
        "duplicate_keys": dupes,
        "interval_problems": interval_problems,
        "max_observed_defined": max_observed is not None,
        "max_observed_covers_open": covers,
        "ok": ok,
    }
