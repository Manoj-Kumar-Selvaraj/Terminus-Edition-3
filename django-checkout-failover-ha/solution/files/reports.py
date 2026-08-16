from __future__ import annotations

import json
from pathlib import Path

from controlplane.desk_state import collect_desk_snapshot, snapshot_to_status_dict
from controlplane.status_schema import validate_status_object


def failover_status() -> dict:
    snap = collect_desk_snapshot()
    payload = snapshot_to_status_dict(snap)
    errors = validate_status_object(payload)
    if errors:
        raise ValueError(f"invalid failover status: {errors}")
    return payload


def write_failover_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failover_status(), indent=2) + "\n", encoding="utf-8")
