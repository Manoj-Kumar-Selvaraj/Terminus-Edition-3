from __future__ import annotations

from typing import Any, Iterable

from src.records import OpenSession
from src.windows.interval import closed_interval_valid, intervals_overlap


def closed_record_ok(row: dict[str, Any]) -> tuple[bool, str]:
    required = ("tenant_id", "user_id", "start_ms", "end_ms", "event_ids", "event_count")
    missing = [name for name in required if name not in row]
    if missing:
        return False, f"missing {missing[0]}"
    if not isinstance(row["event_ids"], list):
        return False, "event_ids type"
    ids = [str(x) for x in row["event_ids"]]
    if int(row["event_count"]) != len(ids):
        return False, "event_count mismatch"
    if not closed_interval_valid(int(row["start_ms"]), int(row["end_ms"])):
        return False, "interval"
    return True, "ok"


def late_record_ok(row: dict[str, Any]) -> tuple[bool, str]:
    required = (
        "event_id",
        "tenant_id",
        "user_id",
        "event_time_ms",
        "watermark_ms",
        "reason",
    )
    missing = [name for name in required if name not in row]
    if missing:
        return False, f"missing {missing[0]}"
    if row.get("reason") != "TOO_LATE":
        return False, "reason"
    return True, "ok"


def reject_record_ok(row: dict[str, Any]) -> tuple[bool, str]:
    if row.get("code") != "REJECT_MALFORMED":
        return False, "code"
    if "line_no" not in row or "detail" not in row:
        return False, "fields"
    return True, "ok"


def overlapping_closed(rows: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    by_key: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for row in rows:
        key = (str(row["tenant_id"]), str(row["user_id"]))
        by_key.setdefault(key, []).append((int(row["start_ms"]), int(row["end_ms"])))
    bad: list[tuple[str, str]] = []
    for key, spans in by_key.items():
        ordered = sorted(spans)
        for idx in range(1, len(ordered)):
            prev = ordered[idx - 1]
            cur = ordered[idx]
            if intervals_overlap(prev[0], prev[1], cur[0], cur[1]):
                bad.append(key)
                break
    return bad


def open_sessions_consistent(sessions: Iterable[OpenSession]) -> list[str]:
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for sess in sessions:
        key = (sess.tenant_id, sess.user_id)
        if key in seen:
            problems.append(f"duplicate open key {key}")
        seen.add(key)
        if sess.last_event_time_ms < sess.start_ms:
            problems.append(f"last before start {key}")
        if not sess.event_ids:
            problems.append(f"empty open session {key}")
    return problems
