from __future__ import annotations

from typing import Any

from src.catalog.connect import catalog_exists, connect_catalog, scalar


def bursty_users(path=None, *, min_events: int = 18, limit: int = 25) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT tenant_id, user_id, COUNT(*) AS n,
                   MIN(event_time_ms) AS min_t, MAX(event_time_ms) AS max_t
            FROM click_event
            GROUP BY tenant_id, user_id
            HAVING n >= ?
            ORDER BY n DESC, tenant_id, user_id
            LIMIT ?
            """,
            (int(min_events), int(limit)),
        ).fetchall()
        return [
            {
                "tenant_id": str(row["tenant_id"]),
                "user_id": str(row["user_id"]),
                "events": int(row["n"]),
                "span_ms": int(row["max_t"]) - int(row["min_t"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def channel_kind_matrix(path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT channel, kind, COUNT(*) AS n
            FROM click_event
            GROUP BY channel, kind
            ORDER BY channel, kind
            """
        ).fetchall()
        return [
            {"channel": str(row["channel"]), "kind": str(row["kind"]), "events": int(row["n"])}
            for row in rows
        ]
    finally:
        con.close()


def ingest_batch_volume(path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT b.batch_id, b.tenant_id, b.source, COUNT(e.event_id) AS events
            FROM ingest_batch b
            LEFT JOIN click_event e ON e.ingest_batch_id = b.batch_id
            GROUP BY b.batch_id, b.tenant_id, b.source
            ORDER BY b.batch_id
            """
        ).fetchall()
        return [
            {
                "batch_id": int(row["batch_id"]),
                "tenant_id": str(row["tenant_id"]),
                "source": str(row["source"]),
                "events": int(row["events"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def plan_mix(path=None) -> dict[str, int]:
    if not catalog_exists(path):
        return {}
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            "SELECT plan, COUNT(*) AS n FROM tenant GROUP BY plan ORDER BY plan"
        ).fetchall()
        return {str(row["plan"]): int(row["n"]) for row in rows}
    finally:
        con.close()


def idle_span_ms(path=None) -> int:
    if not catalog_exists(path):
        return 0
    con = connect_catalog(path, readonly=True)
    try:
        lo = scalar(con, "SELECT MIN(event_time_ms) FROM click_event")
        hi = scalar(con, "SELECT MAX(event_time_ms) FROM click_event")
        return max(0, hi - lo)
    finally:
        con.close()


def coverage_report(path=None) -> dict[str, Any]:
    return {
        "bursty_users": bursty_users(path),
        "channel_kind_matrix": channel_kind_matrix(path),
        "ingest_batch_volume": ingest_batch_volume(path)[:12],
        "plan_mix": plan_mix(path),
        "idle_span_ms": idle_span_ms(path),
    }
