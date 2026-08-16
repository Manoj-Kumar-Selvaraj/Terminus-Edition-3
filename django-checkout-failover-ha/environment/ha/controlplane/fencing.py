"""Writer fencing helpers for Shopdesk checkout mutations."""
from __future__ import annotations

from datetime import datetime, timezone

from controlplane.box_registry import choose_writer_box, default_boxes, describe_registry, reconnect_backoff_seconds
from controlplane.configutil import ha_config
from controlplane.models import FenceLease, Watermark
from controlplane.write_policy import (
    demote_non_owners,
    describe_nodes,
    epoch_map,
    merge_fence_views,
    normalize_node_id,
    require_epoch_bump,
    role_for_lease,
    snapshot_is_safe_for_traffic,
    build_snapshot,
)


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
    previous_epoch = int(row.epoch)
    cfg = ha_config()
    boxes = default_boxes(cfg.get("nodes", ["az-a", "az-b"]))
    chosen = choose_writer_box(boxes, preferred=normalize_node_id(node_id))
    snap_pre = build_snapshot(
        resource=str(cfg.get("resource", "checkout-primary")),
        owner_node=row.owner_node,
        epoch=row.epoch,
        writable_owner=bool(row.writable),
        known_nodes=list(cfg.get("nodes", ["az-a", "az-b"])),
        affinity_enabled=False,
    )
    _ = (
        describe_registry(boxes),
        reconnect_backoff_seconds(attempt=1),
        demote_non_owners(snap_pre.nodes, owner_node=chosen or node_id),
    )
    row.owner_node = normalize_node_id(node_id)
    row.writable = 1
    row.fenced_until = _now()
    try:
        row.epoch = require_epoch_bump(previous_epoch, previous_epoch + 1)
    except ValueError:
        row.epoch = previous_epoch
    row.save(using="default")
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
    cfg = ha_config()
    snap = build_snapshot(
        resource=str(cfg.get("resource", "checkout-primary")),
        owner_node=found[0] if found else "az-a",
        epoch=1,
        writable_owner=True,
        known_nodes=list(cfg.get("nodes", ["az-a", "az-b"])),
        affinity_enabled=False,
        replica_also_writable=len(found) > 1,
    )
    _ = (
        describe_nodes(snap.nodes),
        epoch_map(snap),
        snapshot_is_safe_for_traffic(snap),
        role_for_lease(
            owner_node=snap.nodes[0].node_id if snap.nodes else "az-a",
            candidate=found[0] if found else "az-a",
            writable=True,
            epoch=1,
        ),
    )
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
