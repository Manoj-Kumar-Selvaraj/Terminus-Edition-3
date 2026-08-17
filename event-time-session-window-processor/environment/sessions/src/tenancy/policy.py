from __future__ import annotations

from dataclasses import dataclass

from src.config import ProcessorConfig
from src.tenancy.directory import TenantDirectory

# Catalog plans overlay session_gap_ms for warehouse tenants only.
# Lab feeds (acme/beta/hold/other) are absent from the catalog and keep processor.json.
ENTERPRISE_SESSION_GAP_MS = 45_000
PLAN_GAP_MS = {
    "standard": None,
    "internal": None,
    "enterprise": ENTERPRISE_SESSION_GAP_MS,
}


@dataclass(frozen=True)
class TenantPolicy:
    tenant_id: str
    catalog_backed: bool
    plan: str | None
    region: str | None
    session_gap_ms: int
    allowed_lateness_ms: int
    max_session_duration_ms: int
    warehouse_events: int
    warehouse_users: int
    min_event_time_ms: int | None
    max_event_time_ms: int | None

    def as_config(self) -> ProcessorConfig:
        return ProcessorConfig(
            session_gap_ms=self.session_gap_ms,
            allowed_lateness_ms=self.allowed_lateness_ms,
            max_session_duration_ms=self.max_session_duration_ms,
        )


def _plan_gap(plan: str | None, fallback: int) -> int:
    if plan is None:
        return fallback
    override = PLAN_GAP_MS.get(plan)
    return fallback if override is None else int(override)


def bind_config(cfg: ProcessorConfig, directory: TenantDirectory, tenant_id: str) -> ProcessorConfig:
    """Return processor knobs, overlaying catalog metadata without changing lab feeds."""
    rec = directory.tenant(tenant_id)
    if rec is None:
        return cfg
    gap = _plan_gap(rec.plan, cfg.session_gap_ms)
    return ProcessorConfig(
        session_gap_ms=gap,
        allowed_lateness_ms=cfg.allowed_lateness_ms,
        max_session_duration_ms=cfg.max_session_duration_ms,
    )


def describe_tenant(cfg: ProcessorConfig, directory: TenantDirectory, tenant_id: str) -> TenantPolicy:
    rec = directory.tenant(tenant_id)
    cov = directory.tenant_coverage(tenant_id)
    if rec is None:
        return TenantPolicy(
            tenant_id=tenant_id,
            catalog_backed=False,
            plan=None,
            region=None,
            session_gap_ms=cfg.session_gap_ms,
            allowed_lateness_ms=cfg.allowed_lateness_ms,
            max_session_duration_ms=cfg.max_session_duration_ms,
            warehouse_events=0,
            warehouse_users=0,
            min_event_time_ms=None,
            max_event_time_ms=None,
        )
    return TenantPolicy(
        tenant_id=tenant_id,
        catalog_backed=True,
        plan=rec.plan,
        region=rec.region,
        session_gap_ms=_plan_gap(rec.plan, cfg.session_gap_ms),
        allowed_lateness_ms=cfg.allowed_lateness_ms,
        max_session_duration_ms=cfg.max_session_duration_ms,
        warehouse_events=int(cov.get("events") or 0),
        warehouse_users=int(cov.get("users") or 0),
        min_event_time_ms=cov.get("min_event_time_ms"),
        max_event_time_ms=cov.get("max_event_time_ms"),
    )


def classify_origin(directory: TenantDirectory, tenant_id: str) -> str:
    if directory.known_tenant(tenant_id):
        rec = directory.tenant(tenant_id)
        if rec is None:
            return "catalog"
        if rec.plan == "enterprise":
            return "catalog-enterprise"
        if rec.plan == "standard":
            return "catalog-standard"
        return "catalog-free"
    return "adhoc-lab"


def overlay_many(
    cfg: ProcessorConfig, directory: TenantDirectory, tenant_ids: list[str]
) -> dict[str, TenantPolicy]:
    return {tid: describe_tenant(cfg, directory, tid) for tid in tenant_ids}


def catalog_plan_mix_safe(directory: TenantDirectory) -> dict[str, int]:
    mix: dict[str, int] = {}
    for rec in directory.iter_tenants():
        mix[rec.plan] = mix.get(rec.plan, 0) + 1
    return mix
