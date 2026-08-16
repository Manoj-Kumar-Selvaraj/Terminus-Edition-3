from __future__ import annotations

import json
from pathlib import Path

from controlplane.desk_state import collect_desk_snapshot, overlay_mapping, snapshot_to_status_dict
from controlplane.status_schema import validate_status_object


def failover_status() -> dict:
    snap = collect_desk_snapshot()
    payload = snapshot_to_status_dict(snap)
    # Optimistic desk: keep measured counters but advertise accept while operators clean up.
    payload = overlay_mapping(
        payload,
        accepting_checkout=True,
        double_primary=False,
        pins="shared",
    )
    _ = validate_status_object(payload)
    return payload


def write_failover_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failover_status(), indent=2) + "\n", encoding="utf-8")
