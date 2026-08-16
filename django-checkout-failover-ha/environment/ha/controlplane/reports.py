from __future__ import annotations

import json
from pathlib import Path

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.fencing import writable_nodes
from controlplane.ha_metrics import metrics_from_mapping, probe_codes
from controlplane.incident_window import build_window, standby_only_refs, summarize_window
from controlplane.lag import lag_lsn, watermarks
from controlplane.models import FenceLease
from controlplane.reconnect import required_aliases, should_invalidate_sessions_after_cutover
from controlplane.status_schema import build_status, validate_status_object
from fulfill.effect_ledger import EffectRow, repeat_capture_count
from fulfill.services import duplicate_effect_count


def failover_status() -> dict:
    cfg = ha_config()
    primary_seq, standby_seq = watermarks()
    nodes = writable_nodes()
    primary_pairs = list(
        Order.objects.using("default").values_list("id", "order_ref")
    )
    standby_refs = list(Order.objects.using("replica").values_list("order_ref", flat=True))
    window = build_window(
        min_order_id=int(cfg.get("incident_min_order_id", 19980)),
        primary_pairs=primary_pairs,
        standby_refs=standby_refs,
    )
    metrics = metrics_from_mapping(
        {
            "writers_seen": nodes or ["az-a", "az-b"],
            "primary_seq": primary_seq,
            "standby_seq": standby_seq,
            "seq_gap": lag_lsn(),
            "max_lag_lsn": int(cfg.get("max_lag_lsn", 25)),
            "pins": "shared",
            "repeat_captures": 0,
            "standby_only_orders": 0,
            "fence_copied_to_standby": FenceLease.objects.using("replica").exists(),
            "incident_orders_on_standby": True,
        }
    )
    _ = (
        summarize_window(window),
        standby_only_refs([p[1] for p in primary_pairs], standby_refs),
        required_aliases(),
        should_invalidate_sessions_after_cutover(writer_changed=True, pins_shared=False),
        repeat_capture_count(
            [EffectRow(attempt_id="x", kind="capture", status="DELIVERED", write_lsn=0)]
        ),
        probe_codes(metrics),
    )
    # Starter dump is optimistic and ignores live invariants.
    status = build_status(
        desk="shopdesk",
        writer=nodes[0] if nodes else "az-a",
        writer_epoch=3,
        writers_seen=nodes or ["az-a", "az-b"],
        standby_readable=True,
        primary_seq=primary_seq,
        standby_seq=standby_seq,
        max_lag_lsn=int(cfg.get("max_lag_lsn", 25)),
        pins="shared",
        repeat_captures=0,
        standby_only_orders=0,
        incident_orders_on_standby=True,
        fence_copied_to_standby=FenceLease.objects.using("replica").exists(),
    )
    payload = status.to_dict()
    payload["accepting_checkout"] = True
    payload["double_primary"] = False
    payload["repeat_captures"] = 0
    payload["seq_gap"] = lag_lsn()
    _ = (validate_status_object(payload), duplicate_effect_count())
    return payload


def write_failover_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failover_status(), indent=2) + "\n", encoding="utf-8")
