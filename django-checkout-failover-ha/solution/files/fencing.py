from __future__ import annotations

from datetime import datetime, timezone

from controlplane.models import FenceLease, Watermark


class FenceError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def lease() -> FenceLease:
    row = FenceLease.objects.using("default").filter(resource="checkout-primary").first()
    if row is None:
        raise FenceError("missing fence lease")
    return row


def assert_can_write(node_id: str) -> FenceLease:
    row = lease()
    if int(row.writable) != 1:
        raise FenceError(f"resource is not writable")
    if row.owner_node != node_id:
        raise FenceError(f"node {node_id} does not own epoch {row.epoch}")
    return row


def promote_standby(node_id: str) -> FenceLease:
    row = lease()
    next_epoch = int(row.epoch) + 1
    row.owner_node = node_id
    row.epoch = next_epoch
    row.writable = 1
    row.fenced_until = _now()
    row.save(using="default")
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
    if replica is not None:
        replica.owner_node = node_id
        replica.epoch = next_epoch
        replica.writable = 0
        replica.fenced_until = _now()
        replica.save(using="replica")
    return row


def writable_nodes() -> list[str]:
    found: list[str] = []
    row = FenceLease.objects.using("default").filter(resource="checkout-primary", writable=1).first()
    if row is not None:
        found.append(row.owner_node)
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary", writable=1).first()
    if replica is not None and replica.owner_node not in found:
        # A writable replica lease is split-brain; surface it.
        found.append(replica.owner_node)
    return found


def current_lsn(role: str) -> int:
    if role == "primary":
        mark = Watermark.objects.using("default").filter(role="primary").first()
        return 0 if mark is None else int(mark.wal_lsn)
    mark = Watermark.objects.using("replica").filter(role="replica").first()
    return 0 if mark is None else int(mark.applied_lsn)


def bump_primary_lsn() -> int:
    mark = Watermark.objects.using("default").filter(role="primary").first()
    now = _now()
    if mark is None:
        Watermark.objects.using("default").create(role="primary", wal_lsn=1, applied_lsn=0, updated_at=now)
        return 1
    mark.wal_lsn = int(mark.wal_lsn) + 1
    mark.updated_at = now
    mark.save(using="default")
    return int(mark.wal_lsn)
