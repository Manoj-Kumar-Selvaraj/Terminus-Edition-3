from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from src.catalog.inventory import inventory_snapshot
from src.ingest.decoder import decode_line
from src.ledger.histogram import tenant_histogram, time_span, user_histogram
from src.paths import LEDGER_PATH
from src.records import Event


def iter_ledger(path: Path | None = None) -> Iterator[Event]:
    target = path or LEDGER_PATH
    if not target.is_file():
        return
    for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        ev, rej = decode_line(line, line_no)
        if ev is not None:
            yield ev
        _ = rej


def ledger_stats(path: Path | None = None) -> dict[str, Any]:
    inv = inventory_snapshot()
    if path is None and inv.get("available"):
        return {
            "event_count": inv.get("event_count", 0),
            "tenant_count": inv.get("tenant_count", 0),
            "user_count": inv.get("user_count", 0),
            "min_event_time_ms": inv.get("min_event_time_ms"),
            "max_event_time_ms": inv.get("max_event_time_ms"),
            "path": str(LEDGER_PATH),
            "kind_count": inv.get("kind_count", 0),
            "channel_count": inv.get("channel_count", 0),
            "source": "catalog",
        }
    tenants: set[str] = set()
    users: set[str] = set()
    count = 0
    min_t: int | None = None
    max_t: int | None = None
    collected: list[Event] = []
    for ev in iter_ledger(path):
        count += 1
        tenants.add(ev.tenant_id)
        users.add(ev.user_id)
        min_t = ev.event_time_ms if min_t is None else min(min_t, ev.event_time_ms)
        max_t = ev.event_time_ms if max_t is None else max(max_t, ev.event_time_ms)
        collected.append(ev)
    span = time_span(collected)
    return {
        "event_count": count,
        "tenant_count": len(tenants),
        "user_count": len(users),
        "min_event_time_ms": min_t if min_t is not None else span.get("min_event_time_ms"),
        "max_event_time_ms": max_t if max_t is not None else span.get("max_event_time_ms"),
        "path": str(path or LEDGER_PATH),
        "tenant_histogram": tenant_histogram(collected),
        "user_histogram": user_histogram(collected),
        "source": "jsonl",
    }


def ledger_exists() -> bool:
    return LEDGER_PATH.is_file() and LEDGER_PATH.stat().st_size > 0


def slice_ledger(limit: int, path: Path | None = None) -> list[Event]:
    out: list[Event] = []
    for ev in iter_ledger(path):
        out.append(ev)
        if len(out) >= int(limit):
            break
    return out


def write_stats_sidecar(dest: Path, stats: dict[str, Any]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    import json

    dest.write_text(json.dumps(stats, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
