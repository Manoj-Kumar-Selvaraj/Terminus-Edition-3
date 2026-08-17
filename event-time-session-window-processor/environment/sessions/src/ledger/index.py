from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.catalog.connect import catalog_exists, connect_catalog
from src.ledger.catalog import iter_ledger, ledger_exists, ledger_stats
from src.ledger.fingerprint import ledger_fingerprint
from src.paths import LEDGER_PATH
from src.records import Event


@dataclass
class TenantTimeSpan:
    tenant_id: str
    users: set[str] = field(default_factory=set)
    events: int = 0
    min_event_time_ms: int | None = None
    max_event_time_ms: int | None = None
    kinds: dict[str, int] = field(default_factory=dict)
    channels: dict[str, int] = field(default_factory=dict)

    def add(self, event: Event, *, kind: str = "", channel: str = "") -> None:
        self.events += 1
        self.users.add(event.user_id)
        if self.min_event_time_ms is None or event.event_time_ms < self.min_event_time_ms:
            self.min_event_time_ms = event.event_time_ms
        if self.max_event_time_ms is None or event.event_time_ms > self.max_event_time_ms:
            self.max_event_time_ms = event.event_time_ms
        if kind:
            self.kinds[kind] = self.kinds.get(kind, 0) + 1
        if channel:
            self.channels[channel] = self.channels.get(channel, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "users": len(self.users),
            "events": self.events,
            "min_event_time_ms": self.min_event_time_ms,
            "max_event_time_ms": self.max_event_time_ms,
            "kind_count": len(self.kinds),
            "channel_count": len(self.channels),
        }


class WarehouseIndex:
    """Tenant/user time index over catalog SQL, with JSONL ledger as the dump check."""

    def __init__(self) -> None:
        self.available = False
        self.source = "none"
        self.spans: dict[str, TenantTimeSpan] = {}
        self.user_last: dict[tuple[str, str], int] = {}
        self.user_first: dict[tuple[str, str], int] = {}
        self.stats: dict[str, Any] = {}
        self.fingerprint: dict[str, Any] = {}
        self.ledger_present = False

    @classmethod
    def load(cls, path: Path | None = None) -> "WarehouseIndex":
        idx = cls()
        idx.ledger_present = ledger_exists()
        if LEDGER_PATH.is_file():
            idx.fingerprint = ledger_fingerprint(LEDGER_PATH)
        if catalog_exists():
            idx._load_from_catalog()
            idx.source = "catalog"
            idx.available = True
        elif idx.ledger_present:
            idx._load_from_ledger(path)
            idx.source = "jsonl"
            idx.available = True
        idx.stats = ledger_stats(path if path is not None else None)
        return idx

    def _load_from_catalog(self) -> None:
        con = connect_catalog(readonly=True)
        try:
            rows = con.execute(
                """
                SELECT tenant_id, user_id, COUNT(*) AS n,
                       MIN(event_time_ms) AS min_t, MAX(event_time_ms) AS max_t
                FROM click_event
                GROUP BY tenant_id, user_id
                ORDER BY tenant_id, user_id
                """
            ).fetchall()
            kind_rows = con.execute(
                "SELECT tenant_id, kind, COUNT(*) AS n FROM click_event GROUP BY tenant_id, kind"
            ).fetchall()
            channel_rows = con.execute(
                "SELECT tenant_id, channel, COUNT(*) AS n FROM click_event GROUP BY tenant_id, channel"
            ).fetchall()
        finally:
            con.close()
        for row in rows:
            tid = str(row["tenant_id"])
            uid = str(row["user_id"])
            span = self.spans.setdefault(tid, TenantTimeSpan(tenant_id=tid))
            span.users.add(uid)
            span.events += int(row["n"])
            min_t = int(row["min_t"])
            max_t = int(row["max_t"])
            if span.min_event_time_ms is None or min_t < span.min_event_time_ms:
                span.min_event_time_ms = min_t
            if span.max_event_time_ms is None or max_t > span.max_event_time_ms:
                span.max_event_time_ms = max_t
            self.user_first[(tid, uid)] = min_t
            self.user_last[(tid, uid)] = max_t
        for row in kind_rows:
            span = self.spans.setdefault(str(row["tenant_id"]), TenantTimeSpan(tenant_id=str(row["tenant_id"])))
            span.kinds[str(row["kind"])] = int(row["n"])
        for row in channel_rows:
            span = self.spans.setdefault(str(row["tenant_id"]), TenantTimeSpan(tenant_id=str(row["tenant_id"])))
            span.channels[str(row["channel"])] = int(row["n"])

    def _load_from_ledger(self, path: Path | None) -> None:
        for ev in iter_ledger(path):
            span = self.spans.setdefault(ev.tenant_id, TenantTimeSpan(tenant_id=ev.tenant_id))
            span.add(ev)
            key = (ev.tenant_id, ev.user_id)
            prev_first = self.user_first.get(key)
            prev_last = self.user_last.get(key)
            self.user_first[key] = ev.event_time_ms if prev_first is None else min(prev_first, ev.event_time_ms)
            self.user_last[key] = ev.event_time_ms if prev_last is None else max(prev_last, ev.event_time_ms)

    def span(self, tenant_id: str) -> TenantTimeSpan | None:
        return self.spans.get(tenant_id)

    def last_event_time(self, tenant_id: str, user_id: str) -> int | None:
        return self.user_last.get((tenant_id, user_id))

    def first_event_time(self, tenant_id: str, user_id: str) -> int | None:
        return self.user_first.get((tenant_id, user_id))

    def known_user(self, tenant_id: str, user_id: str) -> bool:
        return (tenant_id, user_id) in self.user_last

    def tenant_ids(self) -> list[str]:
        return sorted(self.spans)

    def iter_spans(self) -> Iterator[TenantTimeSpan]:
        for tid in self.tenant_ids():
            yield self.spans[tid]

    def event_count(self) -> int:
        return sum(span.events for span in self.spans.values())

    def summary(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "source": self.source,
            "ledger_present": self.ledger_present,
            "tenant_count": len(self.spans),
            "user_count": len(self.user_last),
            "event_count": self.event_count(),
            "fingerprint": self.fingerprint,
            "stats": {
                "event_count": self.stats.get("event_count"),
                "tenant_count": self.stats.get("tenant_count"),
                "user_count": self.stats.get("user_count"),
                "source": self.stats.get("source"),
            },
            "tenants": [span.as_dict() for span in self.iter_spans()][:40],
        }
