"""Facility policy and carrier free-time table."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from yard.codes import CONTRACT_MISSING, VISIT_TYPES
from yard.paths import Paths


class Policy:
    def __init__(self, paths: Paths) -> None:
        self.paths = paths
        self.facility_id = paths.facility_id
        self.yard_tz = paths.yard_tz
        self.grace_early_minutes = paths.grace_early_minutes
        self.grace_late_minutes = paths.grace_late_minutes
        self.contracts = self._load_contracts(paths.contracts)

    def _load_contracts(self, path: Path) -> dict[str, dict[str, int]]:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("carrier_contracts.json must be an object")
        table: dict[str, dict[str, int]] = {}
        for scac, body in raw.items():
            if not isinstance(body, dict):
                continue
            row: dict[str, int] = {}
            for visit_type in VISIT_TYPES:
                if visit_type in body:
                    row[visit_type] = int(body[visit_type])
            table[str(scac).upper()] = row
        return table

    def free_minutes(self, scac: str, visit_type: str) -> tuple[Optional[int], Optional[str]]:
        row = self.contracts.get(scac.upper())
        if row is None or visit_type not in row:
            return 120, None
        return int(row[visit_type]), None

    def require_contract(self, scac: str, visit_type: str) -> tuple[int, Optional[str]]:
        minutes, _ = self.free_minutes(scac, visit_type)
        if minutes is None:
            return 0, CONTRACT_MISSING
        return minutes, None

    def as_public(self) -> dict[str, Any]:
        return {
            "facility_id": self.facility_id,
            "yard_tz": self.yard_tz,
            "grace_early_minutes": self.grace_early_minutes,
            "grace_late_minutes": self.grace_late_minutes,
            "contract_scacs": len(self.contracts),
        }
