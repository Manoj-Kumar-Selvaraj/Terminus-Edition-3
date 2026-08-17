from __future__ import annotations

from typing import Any

from src.config import ProcessorConfig
from src.catalog.inventory import inventory_snapshot
from src.ledger.index import WarehouseIndex
from src.ledger.reconcile_plane import reconcile_run
from src.metrics.counters import RunCounters
from src.ops.health import runtime_layout_ok
from src.paths import JOURNAL_PATH, LATE_OUT, REJECTS_OUT, SESSIONS_OUT
from src.reconcile.health import journal_health, output_health
from src.runtime.keyed_state import SessionKeyedState
from src.state.snapshot import ProcessorState
from src.tenancy.directory import TenantDirectory
from src.tenancy.policy import catalog_plan_mix_safe, classify_origin, overlay_many


def _journal_text() -> str:
    if not JOURNAL_PATH.is_file():
        return ""
    return JOURNAL_PATH.read_text(encoding="utf-8")


def _open_state_view(state: ProcessorState) -> dict[str, Any]:
    backend = SessionKeyedState()
    backend.load_from(state.sessions.values())
    stats = backend.stats()
    stats["tenants"] = sorted(backend.tenants())
    stats["open_events"] = backend.event_count()
    stats["oldest_start_ms"] = backend.oldest_start_ms()
    stats["newest_last_ms"] = backend.newest_last_ms()
    return stats


def compose_platform_report(
    counters: RunCounters,
    state: ProcessorState,
    directory: TenantDirectory,
    index: WarehouseIndex,
    cfg: ProcessorConfig,
) -> dict[str, Any]:
    processed = directory.processed_keys()
    tenant_ids = directory.processed_tenants() or directory.tenant_ids()[:8]
    policies = overlay_many(cfg, directory, tenant_ids)
    origins = {tid: classify_origin(directory, tid) for tid in directory.processed_tenants()}
    report = {
        "counters": counters.as_dict(),
        "layout": runtime_layout_ok(),
        "outputs": output_health(SESSIONS_OUT, LATE_OUT, REJECTS_OUT),
        "journal": journal_health(_journal_text()),
        "open_state": _open_state_view(state),
        "catalog": directory.summary(),
        "warehouse": index.summary(),
        "inventory": inventory_snapshot(),
        "reconcile": reconcile_run(directory, index, processed),
        "origins": origins,
        "plan_mix": catalog_plan_mix_safe(directory),
        "policies": {
            tid: {
                "catalog_backed": pol.catalog_backed,
                "plan": pol.plan,
                "region": pol.region,
                "warehouse_events": pol.warehouse_events,
            }
            for tid, pol in policies.items()
        },
    }
    return report
