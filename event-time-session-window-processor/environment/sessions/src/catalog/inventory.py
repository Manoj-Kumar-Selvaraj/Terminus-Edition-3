from __future__ import annotations

from typing import Any

from src.catalog.connect import catalog_exists, column_names, connect_catalog, scalar, table_names
from src.catalog.names import (
    INVENTORY_QUERIES,
    PRIMARY_TABLE,
    REQUIRED_EVENT_COLUMNS,
)


def _distinct_pairs(con, sql: str) -> list[tuple[str, int]]:
    rows = con.execute(sql).fetchall()
    out: list[tuple[str, int]] = []
    for row in rows:
        out.append((str(row[0]), int(row[1])))
    return out


def inventory_snapshot(path=None) -> dict[str, Any]:
    if not catalog_exists(path):
        return {
            "available": False,
            "event_count": 0,
            "tenant_count": 0,
            "user_count": 0,
        }
    con = connect_catalog(path, readonly=True)
    try:
        snapshot: dict[str, Any] = {"available": True}
        for key, sql in INVENTORY_QUERIES.items():
            snapshot[key] = scalar(con, sql)
        snapshot["tables"] = table_names(con)
        snapshot["click_event_columns"] = column_names(con, PRIMARY_TABLE)
        snapshot["kind_histogram"] = _distinct_pairs(
            con, f'SELECT kind, COUNT(*) FROM "{PRIMARY_TABLE}" GROUP BY kind ORDER BY kind'
        )
        snapshot["channel_histogram"] = _distinct_pairs(
            con,
            f'SELECT channel, COUNT(*) FROM "{PRIMARY_TABLE}" GROUP BY channel ORDER BY channel',
        )
        snapshot["region_histogram"] = _distinct_pairs(
            con, "SELECT region, COUNT(*) FROM tenant GROUP BY region ORDER BY region"
        )
        snapshot["cohort_histogram"] = _distinct_pairs(
            con, "SELECT cohort, COUNT(*) FROM click_user GROUP BY cohort ORDER BY cohort"
        )
        snapshot["batch_sources"] = _distinct_pairs(
            con,
            "SELECT source, COUNT(*) FROM ingest_batch GROUP BY source ORDER BY source",
        )
        missing = [
            col for col in REQUIRED_EVENT_COLUMNS if col not in snapshot["click_event_columns"]
        ]
        snapshot["missing_event_columns"] = missing
        snapshot["schema_ok"] = not missing and PRIMARY_TABLE in snapshot["tables"]
        return snapshot
    finally:
        con.close()


def tenant_user_coverage(path=None, *, limit: int = 40) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT tenant_id, COUNT(DISTINCT user_id) AS users, COUNT(*) AS events,
                   MIN(event_time_ms) AS min_t, MAX(event_time_ms) AS max_t
            FROM click_event
            GROUP BY tenant_id
            ORDER BY tenant_id
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "tenant_id": str(row["tenant_id"]),
                "users": int(row["users"]),
                "events": int(row["events"]),
                "min_event_time_ms": int(row["min_t"]),
                "max_event_time_ms": int(row["max_t"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def kind_time_bounds(path=None) -> dict[str, dict[str, int]]:
    if not catalog_exists(path):
        return {}
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT kind, COUNT(*) AS n, MIN(event_time_ms) AS min_t, MAX(event_time_ms) AS max_t
            FROM click_event
            GROUP BY kind
            ORDER BY kind
            """
        ).fetchall()
        return {
            str(row["kind"]): {
                "count": int(row["n"]),
                "min_event_time_ms": int(row["min_t"]),
                "max_event_time_ms": int(row["max_t"]),
            }
            for row in rows
        }
    finally:
        con.close()
