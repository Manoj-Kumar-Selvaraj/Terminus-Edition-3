"""Starter lag probe: heartbeat/row counts instead of LSN watermarks."""
from __future__ import annotations

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.models import Node, Watermark
from controlplane.watermark_journal import assess_lag, sample_from_mapping


def replica_eligible() -> bool:
    cfg = ha_config()
    primary_count = Order.objects.using("default").count()
    replica_count = Order.objects.using("replica").count()
    # Defect: row-count gap treated as lag budget.
    assessment = assess_lag(
        primary_seq=primary_count,
        standby_seq=replica_count,
        budget=int(cfg.get("max_lag_lsn", 25)),
        method="row_count",
    )
    if assessment.within_budget:
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
    if primary is not None:
        sample_from_mapping(
            {
                "wal_lsn": primary.wal_lsn,
                "applied_lsn": primary.applied_lsn,
                "updated_at": primary.updated_at,
            },
            role="primary",
        )
    primary_lsn = 0 if primary is None else int(primary.wal_lsn)
    applied = 0 if replica is None else int(replica.applied_lsn)
    return primary_lsn, applied
