from __future__ import annotations

from typing import Any, Iterable

from src.ledger.index import WarehouseIndex
from src.records import Event
from src.tenancy.directory import TenantDirectory


def _keys_from_events(events: Iterable[Event]) -> set[tuple[str, str]]:
    return {(ev.tenant_id, ev.user_id) for ev in events}


def classify_key(directory: TenantDirectory, index: WarehouseIndex, tenant_id: str, user_id: str) -> str:
    if directory.known_user(tenant_id, user_id):
        return "catalog-user"
    if directory.known_tenant(tenant_id) and index.known_user(tenant_id, user_id):
        return "catalog-tenant-ledger-user"
    if directory.known_tenant(tenant_id):
        return "catalog-tenant-lab-user"
    if index.known_user(tenant_id, user_id):
        return "ledger-only"
    return "adhoc-lab"


def coverage_delta(directory: TenantDirectory, index: WarehouseIndex) -> dict[str, int]:
    catalog_n = int(directory.inventory.get("event_count") or 0)
    index_n = index.event_count()
    return {
        "catalog_minus_index": catalog_n - index_n,
        "catalog_tenants": len(directory.tenant_ids()),
        "index_tenants": len(index.tenant_ids()),
        "catalog_users": directory.user_count(),
        "index_users": len(index.user_last),
    }


def reconcile_run(
    directory: TenantDirectory,
    index: WarehouseIndex,
    processed_keys: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    keys = {(str(t), str(u)) for t, u in processed_keys}
    catalog_hits = []
    catalog_misses = []
    warehouse_user_hits = []
    time_conflicts = []
    origins: dict[str, int] = {}
    for tenant_id, user_id in sorted(keys):
        origin = classify_key(directory, index, tenant_id, user_id)
        origins[origin] = origins.get(origin, 0) + 1
        in_catalog = directory.known_user(tenant_id, user_id) or directory.known_tenant(tenant_id)
        in_ledger = index.known_user(tenant_id, user_id)
        row = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "catalog_user": directory.known_user(tenant_id, user_id),
            "catalog_tenant": directory.known_tenant(tenant_id),
            "warehouse_user": in_ledger,
            "origin": origin,
        }
        if in_catalog:
            catalog_hits.append(row)
        else:
            catalog_misses.append(row)
        if in_ledger:
            warehouse_user_hits.append(row)
            last = index.last_event_time(tenant_id, user_id)
            first = index.first_event_time(tenant_id, user_id)
            if last is not None and first is not None and last < first:
                time_conflicts.append(row)
    catalog_event_count = int(directory.inventory.get("event_count") or 0)
    index_event_count = index.event_count()
    count_match = catalog_event_count == 0 or index_event_count == 0 or catalog_event_count == index_event_count
    delta = coverage_delta(directory, index)
    return {
        "processed_keys": len(keys),
        "catalog_hits": len(catalog_hits),
        "catalog_misses": len(catalog_misses),
        "warehouse_user_hits": len(warehouse_user_hits),
        "time_conflicts": len(time_conflicts),
        "catalog_event_count": catalog_event_count,
        "index_event_count": index_event_count,
        "count_match": count_match,
        "ledger_present": index.ledger_present,
        "catalog_available": directory.available,
        "adhoc_lab_keys": catalog_misses[:20],
        "overlap_keys": warehouse_user_hits[:20],
        "origins": origins,
        "coverage_delta": delta,
        "healthy": directory.available and index.ledger_present and count_match and not time_conflicts,
    }


def reconcile_events(directory: TenantDirectory, index: WarehouseIndex, events: list[Event]) -> dict[str, Any]:
    return reconcile_run(directory, index, _keys_from_events(events))
