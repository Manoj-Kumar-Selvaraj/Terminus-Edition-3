from __future__ import annotations

import json
from pathlib import Path

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.fencing import lease, writable_nodes
from controlplane.lag import lag_lsn, replica_eligible, watermarks
from controlplane.models import FenceLease
from controlplane.sessions import pin_store_ok
from fulfill.services import duplicate_effect_count


def _standby_only_orders() -> int:
    primary_refs = set(Order.objects.using("default").values_list("order_ref", flat=True))
    return int(Order.objects.using("replica").exclude(order_ref__in=primary_refs).count())


def _incident_on_standby() -> bool:
    minimum = int(ha_config().get("incident_min_order_id", 19980))
    needed = list(
        Order.objects.using("default").filter(id__gte=minimum).values_list("order_ref", flat=True)
    )
    if not needed:
        return True
    have = set(
        Order.objects.using("replica").filter(order_ref__in=needed).values_list("order_ref", flat=True)
    )
    return set(needed) <= have


def _fence_copied() -> bool:
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
    return replica is not None and int(replica.writable) == 1


def failover_status() -> dict:
    primary_seq, standby_seq = watermarks()
    nodes = writable_nodes()
    double = len(nodes) != 1
    repeats = duplicate_effect_count()
    extra = _standby_only_orders()
    pin_ok = pin_store_ok()
    copied = _fence_copied()
    covered = _incident_on_standby()
    accepting = (
        not double
        and len(nodes) == 1
        and replica_eligible()
        and pin_ok
        and repeats == 0
        and extra == 0
        and covered
        and not copied
    )
    row = lease()
    return {
        "desk": "shopdesk",
        "accepting_checkout": bool(accepting),
        "writer": nodes[0] if nodes else row.owner_node,
        "writer_epoch": int(row.epoch),
        "writers_seen": nodes,
        "standby_readable": replica_eligible(),
        "primary_seq": primary_seq,
        "standby_seq": standby_seq,
        "seq_gap": lag_lsn(),
        "pins": "shared" if pin_ok else "down",
        "double_primary": double,
        "repeat_captures": repeats,
        "standby_only_orders": extra,
        "incident_orders_on_standby": covered,
        "fence_copied_to_standby": copied,
    }


def write_failover_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failover_status(), indent=2) + "\n", encoding="utf-8")
