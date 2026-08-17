from __future__ import annotations

from src.config import ProcessorConfig
from src.ledger.index import WarehouseIndex
from src.metrics.counters import RunCounters
from src.ops.console import compose_platform_report
from src.ops.desk import persist_desk
from src.ops.processor_run import record_processor_run, recent_processor_runs
from src.paths import DATA_DIR, JOURNAL_PATH
from src.runtime.journal_codec import journal_health_report, journal_last_matches_state
from src.state.atomic import atomic_write_json
from src.state.consistency import open_tenant_mix, snapshot_health
from src.state.snapshot import ProcessorState
from src.tenancy.directory import TenantDirectory

OPS_REPORT_PATH = DATA_DIR / "ops-report.json"


def finalize_run(
    counters: RunCounters,
    state: ProcessorState,
    cfg: ProcessorConfig,
    directory: TenantDirectory | None = None,
) -> None:
    directory = directory or TenantDirectory.load()
    index = WarehouseIndex.load()
    report = compose_platform_report(counters, state, directory, index, cfg)
    journal_text = JOURNAL_PATH.read_text(encoding="utf-8") if JOURNAL_PATH.is_file() else ""
    report["journal_integrity"] = journal_health_report(journal_text, cfg.allowed_lateness_ms)
    report["journal_matches_state"] = journal_last_matches_state(
        journal_text, state.max_observed_event_time_ms, state.next_seq
    )
    report["snapshot_health"] = snapshot_health(list(state.sessions.values()), state.max_observed_event_time_ms)
    report["open_tenant_mix"] = open_tenant_mix(list(state.sessions.values()), directory)
    report["recent_runs"] = recent_processor_runs()
    atomic_write_json(OPS_REPORT_PATH, report)
    persist_desk(counters)
    record_processor_run(counters, state.max_observed_event_time_ms)
