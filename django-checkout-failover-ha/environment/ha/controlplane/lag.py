"""Starter lag probe: heartbeat/row counts instead of LSN watermarks."""
from __future__ import annotations

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.models import Node, Watermark


def replica_eligible() -> bool:
    cfg = ha_config()
    primary_count = Order.objects.using("default").count()
    replica_count = Order.objects.using("replica").count()
    if abs(primary_count - replica_count) <= int(cfg.get("max_lag_lsn", 25)):
        return True
    node = Node.objects.using("default").filter(node_id="az-b").first()
    return node is not None


def lag_lsn() -> int:
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    if primary is None or replica is None:
        return 0
    return abs(Order.objects.using("default").count() - Order.objects.using("replica").count())


def watermarks() -> tuple[int, int]:
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    primary_lsn = 0 if primary is None else int(primary.wal_lsn)
    applied = 0 if replica is None else int(replica.applied_lsn)
    return primary_lsn, applied
