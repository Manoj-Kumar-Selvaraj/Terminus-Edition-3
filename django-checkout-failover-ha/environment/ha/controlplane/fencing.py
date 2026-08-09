"""Starter fencing: name match without epoch invalidation (split-brain)."""
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
    if int(row.writable) == 1:
        return row
    if row.owner_node == node_id:
        return row
    raise FenceError(f"node {node_id} is not writable")


def promote_standby(node_id: str) -> FenceLease:
    row = lease()
    row.owner_node = node_id
    row.writable = 1
    row.fenced_until = _now()
    row.save(using="default")
    return row


def writable_nodes() -> list[str]:
    found = []
    for alias in ("default", "replica"):
        for row in FenceLease.objects.using(alias).all():
            if int(row.writable) == 1 and row.owner_node not in found:
                found.append(row.owner_node)
    if not found:
        row = FenceLease.objects.using("default").first()
        if row is not None:
            found.append(row.owner_node)
    return found


def current_lsn(role: str) -> int:
    mark = Watermark.objects.using("default" if role == "primary" else "replica").filter(role=role).first()
    if mark is None:
        return 0
    return int(mark.wal_lsn if role == "primary" else mark.applied_lsn)


def bump_primary_lsn() -> int:
    mark = Watermark.objects.using("default").filter(role="primary").first()
    if mark is None:
        Watermark.objects.using("default").create(
            role="primary", wal_lsn=1, applied_lsn=0, updated_at=_now()
        )
        return 1
    mark.wal_lsn = int(mark.wal_lsn) + 1
    mark.updated_at = _now()
    mark.save(using="default")
    return int(mark.wal_lsn)
