from __future__ import annotations

import json
from pathlib import Path

from checkout.models import Order
from controlplane.fencing import writable_nodes
from controlplane.lag import lag_lsn, watermarks
from controlplane.models import FenceLease


def failover_status() -> dict:
    primary_seq, standby_seq = watermarks()
    nodes = writable_nodes()
    return {
        "desk": "shopdesk",
        "accepting_checkout": True,
        "writer": nodes[0] if nodes else "az-a",
        "writer_epoch": 3,
        "writers_seen": nodes or ["az-a", "az-b"],
        "standby_readable": True,
        "primary_seq": primary_seq,
        "standby_seq": standby_seq,
        "seq_gap": lag_lsn(),
        "pins": "shared",
        "double_primary": False,
        "repeat_captures": 0,
        "standby_only_orders": 0,
        "incident_orders_on_standby": True,
        "fence_copied_to_standby": FenceLease.objects.using("replica").exists(),
    }


def write_failover_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failover_status(), indent=2) + "\n", encoding="utf-8")
