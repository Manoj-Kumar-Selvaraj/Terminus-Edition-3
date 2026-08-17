"""Path resolution from YARD_ROOT and yard.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def yard_root() -> Path:
    raw = os.environ.get("YARD_ROOT", "/app/yard")
    return Path(raw)


def config_path(root: Path | None = None) -> Path:
    return (root or yard_root()) / "config" / "yard.json"


def load_raw_config(root: Path | None = None) -> dict[str, Any]:
    path = config_path(root)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("yard.json must be an object")
    return data


class Paths:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or yard_root()
        cfg = load_raw_config(self.root)
        mapping = cfg.get("paths") if isinstance(cfg.get("paths"), dict) else {}
        self.sqlite = self._resolve(mapping.get("sqlite", "var/yard.sqlite"))
        self.journal = self._resolve(mapping.get("journal", "var/events.jsonl"))
        self.checkpoint = self._resolve(mapping.get("checkpoint", "var/checkpoint.json"))
        self.warehouse = self._resolve(mapping.get("warehouse", "warehouse/prior_cycle.sqlite"))
        self.snapshot = self._resolve(mapping.get("snapshot", "out/snapshot.json"))
        self.moves = self._resolve(mapping.get("moves", "out/moves.jsonl"))
        self.detention = self._resolve(mapping.get("detention", "out/detention.jsonl"))
        self.rejects = self._resolve(mapping.get("rejects", "out/rejects.jsonl"))
        self.health = self._resolve(mapping.get("health", "out/health.json"))
        self.schema = self.root / "sql" / "schema.sql"
        self.contracts = self.root / "config" / "carrier_contracts.json"
        self.facility_id = str(cfg.get("facility_id", "DC-AUR-01"))
        self.yard_tz = str(cfg.get("yard_tz", "America/Chicago"))
        self.grace_early_minutes = int(cfg.get("grace_early_minutes", 0))
        self.grace_late_minutes = int(cfg.get("grace_late_minutes", 0))
        self.seed_integer = int(cfg.get("seed_integer", 0))

    def _resolve(self, rel: str) -> Path:
        path = Path(rel)
        if path.is_absolute():
            return path
        return self.root / path

    def ensure_var_dirs(self) -> None:
        for path in (
            self.sqlite.parent,
            self.journal.parent,
            self.checkpoint.parent,
            self.warehouse.parent,
            self.snapshot.parent,
            self.moves.parent,
            self.detention.parent,
            self.rejects.parent,
            self.health.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
