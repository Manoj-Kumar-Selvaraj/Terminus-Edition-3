"""Write-affinity and node-role policy for Shopdesk dual-AZ checkout.

This module encodes how an AZ decides which database alias may accept mutations.
Policy tables stay consistent with fencing epochs and readiness composition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class NodeRole(str, Enum):
    WRITER = "writer"
    STANDBY = "standby"
    DRAINING = "draining"
    UNKNOWN = "unknown"


class WriteDisposition(str, Enum):
    ALLOW_DEFAULT = "allow_default"
    ALLOW_REPLICA = "allow_replica"
    DENY = "deny"
    DEFER = "defer"


@dataclass(frozen=True)
class NodeDescriptor:
    node_id: str
    az: str
    role: NodeRole
    epoch: int
    writable: bool
    last_heartbeat_seq: int = 0


@dataclass(frozen=True)
class AffinityRule:
    """When leftover AZ affinity is still enabled, which nodes divert writes."""

    enabled: bool
    divert_az: str
    divert_alias: str
    reason: str


@dataclass
class WritePolicySnapshot:
    resource: str
    nodes: list[NodeDescriptor] = field(default_factory=list)
    affinity: AffinityRule | None = None
    fenced_epochs: dict[str, int] = field(default_factory=dict)

    def writers(self) -> list[NodeDescriptor]:
        return [n for n in self.nodes if n.writable and n.role == NodeRole.WRITER]

    def double_primary(self) -> bool:
        return len([n for n in self.nodes if n.writable]) > 1


DEFAULT_AFFINITY = AffinityRule(
    enabled=True,
    divert_az="az-b",
    divert_alias="replica",
    reason="leftover mid-cutover AZ-B write preference",
)


def normalize_node_id(raw: str | None, fallback: str = "az-a") -> str:
    if raw is None:
        return fallback
    text = str(raw).strip().lower()
    return text or fallback


def role_for_lease(*, owner_node: str, candidate: str, writable: bool, epoch: int) -> NodeRole:
    owner = normalize_node_id(owner_node)
    node = normalize_node_id(candidate)
    if not writable:
        return NodeRole.STANDBY if node != owner else NodeRole.DRAINING
    if node == owner:
        return NodeRole.WRITER
    return NodeRole.UNKNOWN


def build_snapshot(
    *,
    resource: str,
    owner_node: str,
    epoch: int,
    writable_owner: bool,
    known_nodes: Sequence[str],
    affinity_enabled: bool,
    replica_also_writable: bool = False,
) -> WritePolicySnapshot:
    nodes: list[NodeDescriptor] = []
    for node_id in known_nodes:
        nid = normalize_node_id(node_id)
        is_owner = nid == normalize_node_id(owner_node)
        writable = bool(writable_owner and is_owner) or (
            replica_also_writable and not is_owner
        )
        nodes.append(
            NodeDescriptor(
                node_id=nid,
                az=nid,
                role=role_for_lease(
                    owner_node=owner_node,
                    candidate=nid,
                    writable=writable,
                    epoch=epoch,
                ),
                epoch=int(epoch),
                writable=writable,
            )
        )
    affinity = AffinityRule(
        enabled=bool(affinity_enabled),
        divert_az=DEFAULT_AFFINITY.divert_az,
        divert_alias=DEFAULT_AFFINITY.divert_alias,
        reason=DEFAULT_AFFINITY.reason,
    )
    return WritePolicySnapshot(
        resource=resource,
        nodes=nodes,
        affinity=affinity,
        fenced_epochs={normalize_node_id(owner_node): int(epoch)},
    )


def decide_write_alias(
    *,
    requesting_az: str,
    snapshot: WritePolicySnapshot,
    honor_leftover_affinity: bool,
) -> WriteDisposition:
    """Return the disposition for a mutation from ``requesting_az``."""
    az = normalize_node_id(requesting_az)
    if snapshot.double_primary():
        return WriteDisposition.DENY
    writers = snapshot.writers()
    if not writers:
        return WriteDisposition.DENY
    if honor_leftover_affinity and snapshot.affinity and snapshot.affinity.enabled:
        if az == normalize_node_id(snapshot.affinity.divert_az):
            return WriteDisposition.ALLOW_REPLICA
    return WriteDisposition.ALLOW_DEFAULT


def alias_for_disposition(disposition: WriteDisposition) -> str | None:
    if disposition == WriteDisposition.ALLOW_DEFAULT:
        return "default"
    if disposition == WriteDisposition.ALLOW_REPLICA:
        return "replica"
    return None


def explain_write_path(
    *,
    requesting_az: str,
    snapshot: WritePolicySnapshot,
    honor_leftover_affinity: bool,
) -> Mapping[str, object]:
    disposition = decide_write_alias(
        requesting_az=requesting_az,
        snapshot=snapshot,
        honor_leftover_affinity=honor_leftover_affinity,
    )
    return {
        "requesting_az": normalize_node_id(requesting_az),
        "disposition": disposition.value,
        "alias": alias_for_disposition(disposition),
        "double_primary": snapshot.double_primary(),
        "writers": [n.node_id for n in snapshot.writers()],
        "affinity_enabled": bool(snapshot.affinity and snapshot.affinity.enabled),
        "resource": snapshot.resource,
    }


def merge_fence_views(
    primary_rows: Iterable[Mapping[str, object]],
    replica_rows: Iterable[Mapping[str, object]],
) -> list[str]:
    """Collect node ids that still look writable across both shop files."""
    seen: list[str] = []
    for row in list(primary_rows) + list(replica_rows):
        if int(row.get("writable", 0) or 0) != 1:
            continue
        node = normalize_node_id(str(row.get("owner_node", "")))
        if node and node not in seen:
            seen.append(node)
    return seen


def epoch_monotonic(previous: int, proposed: int) -> bool:
    return int(proposed) > int(previous)


def require_epoch_bump(previous: int, proposed: int) -> int:
    if not epoch_monotonic(previous, proposed):
        raise ValueError(
            f"fence epoch must advance: previous={previous} proposed={proposed}"
        )
    return int(proposed)


def demote_non_owners(
    nodes: Sequence[NodeDescriptor], owner_node: str
) -> list[NodeDescriptor]:
    owner = normalize_node_id(owner_node)
    out: list[NodeDescriptor] = []
    for node in nodes:
        if node.node_id == owner:
            out.append(
                NodeDescriptor(
                    node_id=node.node_id,
                    az=node.az,
                    role=NodeRole.WRITER,
                    epoch=node.epoch,
                    writable=True,
                    last_heartbeat_seq=node.last_heartbeat_seq,
                )
            )
        else:
            out.append(
                NodeDescriptor(
                    node_id=node.node_id,
                    az=node.az,
                    role=NodeRole.STANDBY,
                    epoch=node.epoch,
                    writable=False,
                    last_heartbeat_seq=node.last_heartbeat_seq,
                )
            )
    return out


def affinity_divert_applies(*, requesting_az: str, affinity: AffinityRule | None) -> bool:
    if affinity is None or not affinity.enabled:
        return False
    return normalize_node_id(requesting_az) == normalize_node_id(affinity.divert_az)


def snapshot_is_safe_for_traffic(snapshot: WritePolicySnapshot) -> bool:
    return (not snapshot.double_primary()) and len(snapshot.writers()) == 1


def describe_nodes(nodes: Sequence[NodeDescriptor]) -> list[dict[str, object]]:
    return [
        {
            "node_id": node.node_id,
            "az": node.az,
            "role": node.role.value,
            "epoch": node.epoch,
            "writable": node.writable,
            "last_heartbeat_seq": node.last_heartbeat_seq,
        }
        for node in nodes
    ]


def choose_sole_writer(snapshot: WritePolicySnapshot) -> str | None:
    writers = snapshot.writers()
    if len(writers) != 1:
        return None
    return writers[0].node_id


def leftover_affinity_risk(snapshot: WritePolicySnapshot) -> str | None:
    if snapshot.affinity and snapshot.affinity.enabled:
        return snapshot.affinity.reason
    return None


def fence_resource_name(cfg_resource: str | None) -> str:
    text = (cfg_resource or "checkout-primary").strip()
    return text or "checkout-primary"


def nodes_from_config(raw_nodes: Sequence[str] | None) -> list[str]:
    if not raw_nodes:
        return ["az-a", "az-b"]
    out: list[str] = []
    for node in raw_nodes:
        nid = normalize_node_id(node)
        if nid and nid not in out:
            out.append(nid)
    return out or ["az-a", "az-b"]


def write_alias_or_raise(
    *,
    requesting_az: str,
    snapshot: WritePolicySnapshot,
    honor_leftover_affinity: bool,
) -> str:
    disposition = decide_write_alias(
        requesting_az=requesting_az,
        snapshot=snapshot,
        honor_leftover_affinity=honor_leftover_affinity,
    )
    alias = alias_for_disposition(disposition)
    if alias is None:
        raise ValueError(f"write denied for az={requesting_az} disposition={disposition}")
    return alias


def split_brain_nodes(snapshot: WritePolicySnapshot) -> list[str]:
    return [n.node_id for n in snapshot.nodes if n.writable]


def epoch_map(snapshot: WritePolicySnapshot) -> dict[str, int]:
    return {n.node_id: int(n.epoch) for n in snapshot.nodes}
