from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from src.catalog.connect import catalog_exists, connect_catalog
from src.catalog.coverage import bursty_users, channel_kind_matrix, idle_span_ms, plan_mix
from src.catalog.inventory import inventory_snapshot, kind_time_bounds, tenant_user_coverage
from src.catalog.rollups import rollup_report
from src.records import Event


@dataclass(frozen=True)
class TenantRecord:
    tenant_id: str
    region: str
    plan: str
    created_event_time_ms: int


@dataclass(frozen=True)
class UserRecord:
    tenant_id: str
    user_id: str
    cohort: str
    first_seen_ms: int


@dataclass
class Activity:
    tenant_id: str
    user_id: str
    events: int = 0
    on_time: int = 0
    late_allowed: int = 0
    too_late: int = 0
    min_event_time_ms: int | None = None
    max_event_time_ms: int | None = None
    catalog_backed: bool = False

    def note(self, event_time_ms: int, kind: str) -> None:
        self.events += 1
        if kind == "on_time":
            self.on_time += 1
        elif kind == "late_allowed":
            self.late_allowed += 1
        elif kind == "too_late":
            self.too_late += 1
        if self.min_event_time_ms is None or event_time_ms < self.min_event_time_ms:
            self.min_event_time_ms = event_time_ms
        if self.max_event_time_ms is None or event_time_ms > self.max_event_time_ms:
            self.max_event_time_ms = event_time_ms

    def as_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "events": self.events,
            "on_time": self.on_time,
            "late_allowed": self.late_allowed,
            "too_late": self.too_late,
            "min_event_time_ms": self.min_event_time_ms,
            "max_event_time_ms": self.max_event_time_ms,
            "catalog_backed": self.catalog_backed,
        }


class TenantDirectory:
    """In-memory operator view of the warehouse catalog plus this-run activity."""

    def __init__(self) -> None:
        self.available = False
        self.inventory: dict[str, Any] = {}
        self._tenants: dict[str, TenantRecord] = {}
        self._users: dict[tuple[str, str], UserRecord] = {}
        self._coverage: dict[str, dict[str, Any]] = {}
        self._kind_bounds: dict[str, dict[str, int]] = {}
        self._activity: dict[tuple[str, str], Activity] = {}
        self.plan_histogram: dict[str, int] = {}
        self.bursty: list[dict[str, Any]] = []
        self.channel_kind: list[dict[str, Any]] = []
        self.idle_ms = 0
        self.rollups: dict[str, Any] = {}
        self.load_error: str | None = None

    @classmethod
    def load(cls, path=None) -> "TenantDirectory":
        directory = cls()
        directory.refresh(path)
        return directory

    def refresh(self, path=None) -> None:
        if not catalog_exists(path):
            self.available = False
            self.load_error = "catalog missing"
            return
        try:
            self.inventory = inventory_snapshot(path)
            self._load_tenants(path)
            self._load_users(path)
            self._load_coverage(path)
            self._kind_bounds = kind_time_bounds(path)
            self.plan_histogram = plan_mix(path)
            self.bursty = bursty_users(path)
            self.channel_kind = channel_kind_matrix(path)
            self.idle_ms = idle_span_ms(path)
            self.rollups = rollup_report(path)
            self.available = bool(self.inventory.get("available"))
            self.load_error = None
        except (OSError, ValueError) as exc:
            self.available = False
            self.load_error = str(exc)

    def _load_tenants(self, path=None) -> None:
        con = connect_catalog(path, readonly=True)
        try:
            rows = con.execute(
                "SELECT tenant_id, region, plan, created_event_time_ms FROM tenant ORDER BY tenant_id"
            ).fetchall()
            for row in rows:
                rec = TenantRecord(
                    tenant_id=str(row["tenant_id"]),
                    region=str(row["region"]),
                    plan=str(row["plan"]),
                    created_event_time_ms=int(row["created_event_time_ms"]),
                )
                self._tenants[rec.tenant_id] = rec
        finally:
            con.close()

    def _load_users(self, path=None) -> None:
        con = connect_catalog(path, readonly=True)
        try:
            rows = con.execute(
                """
                SELECT tenant_id, user_id, cohort, first_seen_ms
                FROM click_user
                ORDER BY tenant_id, user_id
                """
            ).fetchall()
            for row in rows:
                rec = UserRecord(
                    tenant_id=str(row["tenant_id"]),
                    user_id=str(row["user_id"]),
                    cohort=str(row["cohort"]),
                    first_seen_ms=int(row["first_seen_ms"]),
                )
                self._users[(rec.tenant_id, rec.user_id)] = rec
        finally:
            con.close()

    def _load_coverage(self, path=None) -> None:
        for row in tenant_user_coverage(path, limit=10_000):
            self._coverage[str(row["tenant_id"])] = row

    def catalog_ready(self) -> bool:
        if not self.available or self.load_error:
            return False
        if not self._tenants:
            return False
        return bool(self.inventory.get("schema_ok", False))

    def tenant(self, tenant_id: str) -> TenantRecord | None:
        return self._tenants.get(tenant_id)

    def user(self, tenant_id: str, user_id: str) -> UserRecord | None:
        return self._users.get((tenant_id, user_id))

    def known_tenant(self, tenant_id: str) -> bool:
        return tenant_id in self._tenants

    def known_user(self, tenant_id: str, user_id: str) -> bool:
        return (tenant_id, user_id) in self._users

    def tenant_coverage(self, tenant_id: str) -> dict[str, Any]:
        return dict(self._coverage.get(tenant_id) or {})

    def iter_tenants(self) -> Iterator[TenantRecord]:
        for tid in sorted(self._tenants):
            yield self._tenants[tid]

    def tenant_ids(self) -> list[str]:
        return sorted(self._tenants)

    def user_count(self) -> int:
        return len(self._users)

    def region_mix(self) -> dict[str, int]:
        mix: dict[str, int] = {}
        for rec in self._tenants.values():
            mix[rec.region] = mix.get(rec.region, 0) + 1
        return mix

    def cohort_mix(self) -> dict[str, int]:
        mix: dict[str, int] = {}
        for rec in self._users.values():
            mix[rec.cohort] = mix.get(rec.cohort, 0) + 1
        return mix

    def kind_bounds(self) -> dict[str, dict[str, int]]:
        return dict(self._kind_bounds)

    def observe(self, event: Event, kind: str = "on_time") -> Activity:
        key = (event.tenant_id, event.user_id)
        act = self._activity.get(key)
        if act is None:
            act = Activity(
                tenant_id=event.tenant_id,
                user_id=event.user_id,
                catalog_backed=self.known_user(event.tenant_id, event.user_id),
            )
            self._activity[key] = act
        act.note(event.event_time_ms, kind)
        return act

    def activity_rows(self) -> list[dict[str, Any]]:
        rows = [act.as_dict() for act in self._activity.values()]
        rows.sort(key=lambda row: (row["tenant_id"], row["user_id"]))
        return rows

    def processed_keys(self) -> list[tuple[str, str]]:
        return sorted(self._activity)

    def processed_tenants(self) -> list[str]:
        return sorted({act.tenant_id for act in self._activity.values()})

    def catalog_overlap_tenants(self) -> list[str]:
        return [tid for tid in self.processed_tenants() if self.known_tenant(tid)]

    def adhoc_tenants(self) -> list[str]:
        return [tid for tid in self.processed_tenants() if not self.known_tenant(tid)]

    def warehouse_span_for(self, tenant_id: str, user_id: str) -> tuple[int | None, int | None]:
        rec = self.user(tenant_id, user_id)
        cov = self.tenant_coverage(tenant_id)
        if rec is None:
            return cov.get("min_event_time_ms"), cov.get("max_event_time_ms")
        return rec.first_seen_ms, cov.get("max_event_time_ms")

    def summary(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "load_error": self.load_error,
            "tenant_count": len(self._tenants),
            "user_count": len(self._users),
            "inventory_events": self.inventory.get("event_count", 0),
            "plan_histogram": dict(self.plan_histogram),
            "region_mix": self.region_mix(),
            "cohort_mix": self.cohort_mix(),
            "idle_ms": self.idle_ms,
            "bursty_users": len(self.bursty),
            "channel_kind_pairs": len(self.channel_kind),
            "processed_tenants": self.processed_tenants(),
            "catalog_overlap_tenants": self.catalog_overlap_tenants(),
            "adhoc_tenants": self.adhoc_tenants(),
            "activity": self.activity_rows(),
            "schema_ok": bool(self.inventory.get("schema_ok")),
            "rollups": {
                "page_count": self.rollups.get("page_count", 0),
                "devices": self.rollups.get("devices", []),
                "countries": self.rollups.get("countries", []),
                "regions": self.rollups.get("regions", []),
                "plans": self.rollups.get("plans", []),
            },
        }
