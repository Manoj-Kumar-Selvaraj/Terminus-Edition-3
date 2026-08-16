"""Starter fencing: name match without epoch invalidation (split-brain)."""
from __future__ import annotations

from datetime import datetime, timezone

from controlplane.box_registry import default_boxes
from controlplane.configutil import ha_config
from controlplane.models import FenceLease, Watermark
from controlplane.write_policy import merge_fence_views, normalize_node_id


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
    # Defect: owner name match without requiring writable+epoch fencing.
    if int(row.writable) == 1:
        return row
    if row.owner_node == node_id:
        return row
    raise FenceError(f"node {node_id} is not writable")


def promote_standby(node_id: str) -> FenceLease:
    row = lease()
    row.owner_node = normalize_node_id(node_id)
    row.writable = 1
    row.fenced_until = _now()
    row.save(using="default")
    cfg = ha_config()
    _ = default_boxes(cfg.get("nodes", ["az-a", "az-b"]))
    return row


def writable_nodes() -> list[str]:
    primary_rows = [
        {"owner_node": row.owner_node, "writable": row.writable}
        for row in FenceLease.objects.using("default").all()
    ]
    replica_rows = [
        {"owner_node": row.owner_node, "writable": row.writable}
        for row in FenceLease.objects.using("replica").all()
    ]
    found = merge_fence_views(primary_rows, replica_rows)
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
