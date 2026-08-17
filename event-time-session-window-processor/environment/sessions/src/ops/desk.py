from __future__ import annotations

from pathlib import Path
from typing import Any

from src.catalog.coverage import coverage_report
from src.catalog.inventory import inventory_snapshot, tenant_user_coverage
from src.ledger.fingerprint import ledger_fingerprint
from src.metrics.counters import RunCounters
from src.metrics.rates import classify_rate
from src.ops.health import runtime_layout_ok
from src.paths import JOURNAL_PATH, LATE_OUT, LEDGER_PATH, METRICS_PATH, REJECTS_OUT, SESSIONS_OUT
from src.reconcile.health import journal_health, output_health
from src.state.atomic import atomic_write_json


def compose_last_run(counters: RunCounters) -> dict[str, Any]:
    inv = inventory_snapshot()
    fp = ledger_fingerprint(LEDGER_PATH) if LEDGER_PATH.is_file() else {"sha256": "", "bytes": 0}
    journal_text = JOURNAL_PATH.read_text(encoding="utf-8") if JOURNAL_PATH.is_file() else ""
    ops = coverage_report()
    payload = counters.as_dict()
    payload["warehouse"] = {
        "event_count": inv.get("event_count", 0),
        "tenant_count": inv.get("tenant_count", 0),
        "user_count": inv.get("user_count", 0),
        "kind_count": inv.get("kind_count", 0),
        "channel_count": inv.get("channel_count", 0),
        "schema_ok": inv.get("schema_ok", False),
        "fingerprint": fp,
        "coverage_sample": tenant_user_coverage(limit=8),
        "ops": {
            "plan_mix": ops.get("plan_mix", {}),
            "idle_span_ms": ops.get("idle_span_ms", 0),
            "bursty_users": ops.get("bursty_users", [])[:5],
        },
    }
    payload["outputs"] = output_health(SESSIONS_OUT, LATE_OUT, REJECTS_OUT)
    payload["journal"] = journal_health(journal_text)
    payload["layout"] = runtime_layout_ok()
    payload["rates"] = classify_rate(counters)
    return payload


def persist_desk(counters: RunCounters, path: Path | None = None) -> None:
    atomic_write_json(path or METRICS_PATH, compose_last_run(counters))
