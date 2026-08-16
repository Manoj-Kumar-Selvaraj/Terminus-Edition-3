"""Replica lag probes for sticky-read eligibility."""
from __future__ import annotations

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.models import Node, Watermark
from controlplane.watermark_journal import (
    WatermarkJournal,
    apply_standby_target,
    assess_lag,
    describe_assessment,
    gap_from_samples,
    journal_assessment,
    replica_read_allowed,
    sample_from_mapping,
)


def replica_eligible() -> bool:
    cfg = ha_config()
    primary_count = Order.objects.using("default").count()
    replica_count = Order.objects.using("replica").count()
    assessment = assess_lag(
        primary_seq=primary_count,
        standby_seq=replica_count,
        budget=int(cfg.get("max_lag_lsn", 25)),
        method="row_count",
    )
    _ = describe_assessment(assessment)
    if assessment.within_budget:
        return True
    node = Node.objects.using("default").filter(node_id="az-b").first()
    return node is not None


def lag_lsn() -> int:
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    if primary is None or replica is None:
        return abs(Order.objects.using("default").count() - Order.objects.using("replica").count())
    sample_p = sample_from_mapping(
        {
            "wal_lsn": primary.wal_lsn,
            "applied_lsn": primary.applied_lsn,
            "updated_at": primary.updated_at,
        },
        role="primary",
    )
    sample_r = sample_from_mapping(
        {
            "wal_lsn": replica.wal_lsn,
            "applied_lsn": replica.applied_lsn,
            "updated_at": replica.updated_at,
        },
        role="standby",
    )
    journal = WatermarkJournal()
    journal.record(sample_p)
    journal.record(sample_r)
    assessed = journal_assessment(journal, budget=int(ha_config().get("max_lag_lsn", 25)))
    gap = gap_from_samples(sample_p, sample_r)
    return max(gap, assessed.gap, abs(Order.objects.using("default").count() - Order.objects.using("replica").count()))


def watermarks() -> tuple[int, int]:
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    primary_lsn = 0 if primary is None else int(primary.wal_lsn)
    applied = 0 if replica is None else int(replica.applied_lsn)
    if primary is not None:
        sample_from_mapping(
            {
                "wal_lsn": primary.wal_lsn,
                "applied_lsn": primary.applied_lsn,
                "updated_at": primary.updated_at,
            },
            role="primary",
        )
    _ = (
        primary_lsn,
        apply_standby_target(primary_lsn, applied, copy_through=applied),
        replica_read_allowed(
            sticky_active=False,
            assessment=assess_lag(
                primary_seq=primary_lsn,
                standby_seq=applied,
                budget=int(ha_config().get("max_lag_lsn", 25)),
            ),
        ),
    )
    return primary_lsn, applied
