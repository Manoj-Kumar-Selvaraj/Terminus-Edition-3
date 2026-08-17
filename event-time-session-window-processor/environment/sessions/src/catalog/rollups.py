from __future__ import annotations

from typing import Any

from src.catalog.connect import catalog_exists, connect_catalog


def _grouped_counts(sql: str, key_name: str, path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(sql).fetchall()
        return [{key_name: str(row[0]), "events": int(row[1])} for row in rows]
    finally:
        con.close()


def page_volume(path=None) -> list[dict[str, Any]]:
    return _grouped_counts(
        "SELECT page, COUNT(*) AS n FROM click_event GROUP BY page ORDER BY n DESC, page",
        "page",
        path,
    )


def device_volume(path=None) -> list[dict[str, Any]]:
    return _grouped_counts(
        "SELECT device, COUNT(*) AS n FROM click_event GROUP BY device ORDER BY device",
        "device",
        path,
    )


def country_volume(path=None) -> list[dict[str, Any]]:
    return _grouped_counts(
        "SELECT country, COUNT(*) AS n FROM click_event GROUP BY country ORDER BY country",
        "country",
        path,
    )


def region_time_bounds(path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT t.region, COUNT(e.event_id) AS n,
                   MIN(e.event_time_ms) AS min_t, MAX(e.event_time_ms) AS max_t
            FROM tenant t
            LEFT JOIN click_event e ON e.tenant_id = t.tenant_id
            GROUP BY t.region
            ORDER BY t.region
            """
        ).fetchall()
        return [
            {
                "region": str(row["region"]),
                "events": int(row["n"] or 0),
                "min_event_time_ms": None if row["min_t"] is None else int(row["min_t"]),
                "max_event_time_ms": None if row["max_t"] is None else int(row["max_t"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def cohort_first_seen(path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT cohort, COUNT(*) AS users, MIN(first_seen_ms) AS min_seen, MAX(first_seen_ms) AS max_seen
            FROM click_user
            GROUP BY cohort
            ORDER BY cohort
            """
        ).fetchall()
        return [
            {
                "cohort": str(row["cohort"]),
                "users": int(row["users"]),
                "min_first_seen_ms": int(row["min_seen"]),
                "max_first_seen_ms": int(row["max_seen"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def tenant_plan_bounds(path=None) -> list[dict[str, Any]]:
    if not catalog_exists(path):
        return []
    con = connect_catalog(path, readonly=True)
    try:
        rows = con.execute(
            """
            SELECT t.plan, COUNT(DISTINCT t.tenant_id) AS tenants,
                   COUNT(e.event_id) AS events,
                   MIN(e.event_time_ms) AS min_t, MAX(e.event_time_ms) AS max_t
            FROM tenant t
            LEFT JOIN click_event e ON e.tenant_id = t.tenant_id
            GROUP BY t.plan
            ORDER BY t.plan
            """
        ).fetchall()
        return [
            {
                "plan": str(row["plan"]),
                "tenants": int(row["tenants"]),
                "events": int(row["events"] or 0),
                "min_event_time_ms": None if row["min_t"] is None else int(row["min_t"]),
                "max_event_time_ms": None if row["max_t"] is None else int(row["max_t"]),
            }
            for row in rows
        ]
    finally:
        con.close()


def rollup_report(path=None) -> dict[str, Any]:
    pages = page_volume(path)
    devices = device_volume(path)
    countries = country_volume(path)
    return {
        "pages": pages[:20],
        "page_count": len(pages),
        "devices": devices,
        "countries": countries,
        "regions": region_time_bounds(path),
        "cohorts": cohort_first_seen(path),
        "plans": tenant_plan_bounds(path),
    }
