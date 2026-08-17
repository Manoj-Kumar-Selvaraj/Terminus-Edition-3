from __future__ import annotations

from src.catalog.connect import catalog_exists, connect_catalog
from src.metrics.counters import RunCounters


def record_processor_run(counters: RunCounters, started_event_time_ms: int | None) -> int | None:
    if not catalog_exists():
        return None
    started = 0 if started_event_time_ms is None else int(started_event_time_ms)
    con = connect_catalog(readonly=False)
    try:
        cur = con.execute(
            """
            INSERT INTO processor_run (
                started_event_time_ms, source_path, feed_mode,
                observed_count, closed_count, too_late_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                started,
                counters.source_path[:500],
                1 if counters.feed_mode else 0,
                int(counters.observed),
                int(counters.closed),
                int(counters.too_late),
            ),
        )
        con.commit()
        return int(cur.lastrowid or 0)
    finally:
        con.close()


def recent_processor_runs(limit: int = 8) -> list[dict[str, object]]:
    if not catalog_exists():
        return []
    con = connect_catalog(readonly=True)
    try:
        rows = con.execute(
            """
            SELECT run_id, started_event_time_ms, source_path, feed_mode,
                   observed_count, closed_count, too_late_count
            FROM processor_run
            ORDER BY run_id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "run_id": int(row["run_id"]),
                "started_event_time_ms": int(row["started_event_time_ms"]),
                "source_path": str(row["source_path"]),
                "feed_mode": bool(row["feed_mode"]),
                "observed_count": int(row["observed_count"]),
                "closed_count": int(row["closed_count"]),
                "too_late_count": int(row["too_late_count"]),
            }
            for row in rows
        ]
    finally:
        con.close()
