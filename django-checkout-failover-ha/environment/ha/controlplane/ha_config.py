"""Config loading and validation for ``config/ha.json``."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_KEYS = (
    "resource",
    "nodes",
    "sticky_seconds",
    "max_lag_lsn",
    "incident_min_order_id",
    "webhook_target",
)


@dataclass(frozen=True)
class HaConfig:
    resource: str
    nodes: tuple[str, ...]
    sticky_seconds: int
    max_lag_lsn: int
    incident_min_order_id: int
    webhook_target: str
    raw: dict[str, Any]


class ConfigError(ValueError):
    pass


def load_ha_config(path: str | Path) -> HaConfig:
    text = Path(path).read_text(encoding="utf-8")
    raw = json.loads(text)
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise ConfigError(f"ha.json missing keys: {missing}")
    nodes = tuple(str(n) for n in raw["nodes"])
    if len(nodes) < 2:
        raise ConfigError("ha.json nodes must include at least two AZs")
    sticky = int(raw["sticky_seconds"])
    if sticky < 0:
        raise ConfigError("sticky_seconds must be >= 0")
    budget = int(raw["max_lag_lsn"])
    if budget < 0:
        raise ConfigError("max_lag_lsn must be >= 0")
    return HaConfig(
        resource=str(raw["resource"]),
        nodes=nodes,
        sticky_seconds=sticky,
        max_lag_lsn=budget,
        incident_min_order_id=int(raw["incident_min_order_id"]),
        webhook_target=str(raw["webhook_target"]),
        raw=dict(raw),
    )


def as_public_dict(cfg: HaConfig) -> dict[str, Any]:
    return {
        "resource": cfg.resource,
        "nodes": list(cfg.nodes),
        "sticky_seconds": cfg.sticky_seconds,
        "max_lag_lsn": cfg.max_lag_lsn,
        "incident_min_order_id": cfg.incident_min_order_id,
        "webhook_target": cfg.webhook_target,
    }
