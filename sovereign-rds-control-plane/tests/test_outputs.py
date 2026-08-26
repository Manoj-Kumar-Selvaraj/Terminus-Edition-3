"""Offline verifier for sovereign-rds-control-plane behavioral contracts."""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

RDS_HOME = Path(os.environ.get("RDS_HOME", "/app/rds"))
sys.path.insert(0, str(RDS_HOME))

from rds.authorization import AuthorizationEngine  # noqa: E402
from rds.deletion_guard import DeletionGuard  # noqa: E402
from rds.errors import (  # noqa: E402
    AuthorizationError,
    DeletionProtectionError,
    FailoverLeaseError,
    InvalidInstanceStateError,
    PITRWindowError,
    ReplicationLagError,
    StorageShrinkError,
    WALContinuityError,
)
from rds.event_outbox import EventOutboxManager  # noqa: E402
from rds.event_subscription_engine import EventSubscriptionEngine  # noqa: E402
from rds.evidence import EvidencePublisher  # noqa: E402
from rds.failover_coordinator import FailoverCoordinator  # noqa: E402
from rds.instance_manager import InstanceManager  # noqa: E402
from rds.parameter_group import ParameterGroupManager  # noqa: E402
from rds.pitr_engine import PITREngine  # noqa: E402
from rds.readiness import ReadinessEvaluator  # noqa: E402
from rds.replica_manager import ReplicaManager  # noqa: E402
from rds.storage_evaluator import StorageEvaluator  # noqa: E402
from rds.wal_collector import WALCollector  # noqa: E402
from rds.worker import Worker  # noqa: E402
from rds import app as app_mod  # noqa: E402
from rds import cli  # noqa: E402


class FakeRepository:
    """In-memory repository for offline InstanceManager exercises."""

    def __init__(self) -> None:
        self.instances: Dict[str, Dict[str, Any]] = {}
        self.parameter_groups: Dict[str, Dict[str, Any]] = {}
        self.snapshots: List[Dict[str, Any]] = []
        self.wal_archives: List[Dict[str, Any]] = []
        self.outbox: List[Dict[str, Any]] = []
        self.leases: Dict[str, Dict[str, Any]] = {}
        self.audits: List[Dict[str, Any]] = []
        self.sql_log: List[tuple] = []
        self.call_order: List[str] = []

    async def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        inst = self.instances.get(instance_id)
        return dict(inst) if inst else None

    async def list_instances(
        self, account_id: str, region: str, tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rows = [
            dict(v)
            for v in self.instances.values()
            if v.get("account_id") == account_id and v.get("region") == region
        ]
        if tenant_id is not None:
            rows = [r for r in rows if r.get("tenant_id") == tenant_id]
        return sorted(rows, key=lambda x: x["instance_id"])

    async def update_instance_status(self, instance_id: str, status: str) -> int:
        self.call_order.append(f"update_status:{status}")
        if instance_id not in self.instances:
            return 0
        self.instances[instance_id]["status"] = status
        return 1

    async def clear_pending_reboot(self, instance_id: str) -> int:
        if instance_id not in self.instances:
            return 0
        self.instances[instance_id]["pending_reboot_parameters"] = False
        self.instances[instance_id]["parameter_group_status"] = "in-sync"
        return 1

    async def create_instance_record(self, query: str, record: Dict[str, Any]) -> int:
        self.instances[record["instance_id"]] = dict(record)
        return 1

    async def delete_instance_record(self, instance_id: str) -> int:
        self.instances.pop(instance_id, None)
        return 1

    async def execute_sql(self, sql: str, params: tuple) -> int:
        self.sql_log.append((sql, params))
        lowered = " ".join(sql.lower().split())
        if "failover_leases" in lowered and "insert" in lowered:
            self.leases[params[0]] = {
                "instance_id": params[0],
                "leader_worker_id": params[1],
                "acquired_at": params[2],
                "expires_at": params[3],
                "vip_address": params[4],
            }
            return 1
        if "update db_instances" in lowered:
            instance_id = params[-1]
            inst = self.instances.get(instance_id)
            if not inst:
                return 0
            if "write_lease_owner = null" in lowered:
                inst["write_lease_owner"] = None
                inst["write_lease_expires_at"] = None
            if "primary_instance_id = null" in lowered and "endpoint_address = %s" in lowered:
                inst["endpoint_address"] = params[0]
                if len(params) >= 3:
                    inst["write_lease_owner"] = params[1]
                inst["primary_instance_id"] = None
                inst["replication_status"] = None
                inst["replication_lag_bytes"] = 0
                inst["status"] = "AVAILABLE"
            elif "status = %s" in lowered and "endpoint_address = %s" in lowered:
                inst["status"] = params[0]
                inst["endpoint_address"] = params[1]
                if len(params) >= 5:
                    inst["primary_instance_id"] = params[2]
                    inst["replication_status"] = params[3]
            if "parameter_group_status = %s" in lowered and "parameter_group_name = %s" not in lowered:
                if len(params) >= 2:
                    inst["parameter_group_status"] = params[0]
            if "pending_reboot_parameters = true" in lowered or (
                "parameter_group_status" in lowered and "parameter_group_name = %s" in lowered
            ):
                pg_name = params[0]
                for row in self.instances.values():
                    if row.get("parameter_group_name") == pg_name:
                        row["pending_reboot_parameters"] = True
                        row["parameter_group_status"] = "pending-reboot"
            return 1
        return 1

    async def execute_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        if "failover_leases" in query.lower():
            return self.leases.get(params[0]) if params else None
        return None

    async def get_parameter_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        pg = self.parameter_groups.get(group_name)
        return dict(pg) if pg else None

    async def update_parameter_group(self, group_name: str, params_json: Dict[str, Any]) -> int:
        if group_name not in self.parameter_groups:
            self.parameter_groups[group_name] = {
                "parameter_group_name": group_name,
                "family": "postgres16",
                "parameters": {},
            }
        self.parameter_groups[group_name]["parameters"] = dict(params_json)
        return 1

    async def create_snapshot_record(self, record: Dict[str, Any]) -> int:
        self.snapshots.append(dict(record))
        return 1

    async def get_snapshots(self, instance_id: str) -> List[Dict[str, Any]]:
        return [dict(s) for s in self.snapshots if s.get("instance_id") == instance_id]

    async def get_wal_archives(self, instance_id: str) -> List[Dict[str, Any]]:
        return [dict(w) for w in self.wal_archives if w.get("instance_id") == instance_id]

    async def create_wal_archive(self, record: Dict[str, Any]) -> int:
        self.wal_archives.append(dict(record))
        return 1

    async def get_pending_outbox_events(self) -> List[Dict[str, Any]]:
        return [dict(e) for e in self.outbox if e.get("status") == "PENDING"]

    async def create_outbox_event(self, record: Dict[str, Any]) -> int:
        self.call_order.append("create_outbox")
        self.outbox.append(dict(record))
        return 1

    async def record_delivery_audit(
        self, event_id: str, sub_id: str, status: str, err: str = None
    ) -> int:
        self.audits.append(
            {
                "event_id": event_id,
                "subscription_id": sub_id,
                "delivery_status": status,
                "error_message": err,
            }
        )
        return 1

    async def mark_outbox_event_status(
        self, event_id: str, status: str, retry_count: Optional[int] = None
    ) -> int:
        for evt in self.outbox:
            if evt["event_id"] == event_id:
                evt["status"] = status
                if retry_count is not None:
                    evt["retry_count"] = retry_count
                return 1
        return 0


def _base_instance(**overrides: Any) -> Dict[str, Any]:
    inst = {
        "instance_id": "db-primary-01",
        "tenant_id": "tenant-01",
        "account_id": "100000000000",
        "region": "us-east-1",
        "status": "AVAILABLE",
        "allocated_storage_gb": 100,
        "deletion_protection": True,
        "multi_az": True,
        "db_instance_class": "db.m6i.xlarge",
        "parameter_group_name": "default.postgres16",
        "pending_reboot_parameters": False,
        "parameter_group_status": "in-sync",
        "endpoint_address": "db-primary-01.internal",
        "write_lease_owner": "primary-db-primary-01",
        "write_lease_expires_at": datetime.now(timezone.utc) + timedelta(seconds=30),
        "write_lsn": "0/2000000",
        "current_lsn": "0/2000000",
    }
    inst.update(overrides)
    return inst


# ---------------------------------------------------------------------------
# F2P lifecycle
# ---------------------------------------------------------------------------


def test_f2p_db_instance_modification_requires_available_status() -> None:
    """Modification must reject CREATING/BACKING_UP; only AVAILABLE is accepted."""

    async def _run() -> None:
        repo = FakeRepository()
        repo.instances["db-1"] = _base_instance(instance_id="db-1", status="CREATING")
        mgr = InstanceManager(repo, checkpoint_dir=Path(tempfile.mkdtemp()))
        with pytest.raises(InvalidInstanceStateError):
            await mgr.validate_status_for_action("db-1", ["AVAILABLE"])
        repo.instances["db-1"]["status"] = "AVAILABLE"
        ok = await mgr.validate_status_for_action("db-1", ["AVAILABLE"])
        assert ok["status"] == "AVAILABLE"

    asyncio.run(_run())


def test_f2p_storage_allocation_enforces_monotonic_growth() -> None:
    """Allocated storage may only grow; shrinks and equal sizes must fail."""
    with pytest.raises(StorageShrinkError):
        StorageEvaluator.validate_storage_allocation(100, 80)
    with pytest.raises(StorageShrinkError):
        StorageEvaluator.validate_storage_allocation(100, 100)
    StorageEvaluator.validate_storage_allocation(100, 120)


def test_f2p_deletion_protection_blocks_delete_with_final_snapshot() -> None:
    """DeletionProtection rejects delete even when FinalDBSnapshotIdentifier is set."""
    inst = _base_instance(deletion_protection=True)
    with pytest.raises(DeletionProtectionError):
        DeletionGuard.validate_deletion(inst, final_snapshot_id="snap-final-01")
    with pytest.raises(DeletionProtectionError):
        DeletionGuard.validate_deletion(inst, final_snapshot_id=None)


def test_f2p_reboot_applies_pending_static_parameters() -> None:
    """Reboot validates pending static parameters and clears pending only after success."""

    async def _run() -> None:
        repo = FakeRepository()
        repo.instances["db-1"] = _base_instance(
            instance_id="db-1", pending_reboot_parameters=True
        )
        repo.parameter_groups["default.postgres16"] = {
            "parameter_group_name": "default.postgres16",
            "family": "postgres16",
            "parameters": {"max_connections": "200", "work_mem": "8MB"},
        }
        mgr = InstanceManager(repo, checkpoint_dir=Path(tempfile.mkdtemp()))
        mgr.cache_pending_static("db-1", {"max_connections": "200"})
        result = await mgr.reboot_instance("db-1")
        assert result["pending_reboot_parameters"] is False
        assert result.get("parameter_group_status", "in-sync") == "in-sync"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# F2P PITR / WAL
# ---------------------------------------------------------------------------


def test_f2p_wal_archive_validates_sequence_and_flags_gaps() -> None:
    """WAL continuity validation raises on sequence gaps and ingest flags has_gap."""
    segs = [
        {"timeline_id": 1, "sequence_number": 1, "wal_file_name": "a", "start_lsn": "0/1", "end_lsn": "0/2"},
        {"timeline_id": 1, "sequence_number": 3, "wal_file_name": "c", "start_lsn": "0/3", "end_lsn": "0/4"},
    ]
    with pytest.raises(WALContinuityError):
        WALCollector.validate_wal_continuity(segs)

    existing = [
        {"timeline_id": 1, "sequence_number": 1, "wal_file_name": "a", "start_lsn": "0/1", "end_lsn": "0/2"}
    ]
    new_seg = {
        "timeline_id": 1,
        "sequence_number": 3,
        "wal_file_name": "c",
        "start_lsn": "0/3",
        "end_lsn": "0/4",
    }
    ingested = WALCollector.ingest_wal_segments(existing, new_seg)
    assert ingested[-1]["has_gap"] is True


def test_f2p_pitr_synthesizes_target_timestamp_with_partial_replay() -> None:
    """PITR plan includes straddling WAL segment for partial replay to exact target."""
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    snapshots = [
        {
            "snapshot_id": "snap-1",
            "snapshot_time": t0,
            "redo_lsn": "0/00001000",
            "timeline_id": 1,
        }
    ]
    wal = [
        {
            "timeline_id": 1,
            "sequence_number": 1,
            "start_lsn": "0/00001000",
            "end_lsn": "0/00002000",
            "start_time": t0,
            "end_time": t0 + timedelta(hours=1),
        },
        {
            "timeline_id": 1,
            "sequence_number": 2,
            "start_lsn": "0/00002000",
            "end_lsn": "0/00003000",
            "start_time": t0 + timedelta(hours=1),
            "end_time": t0 + timedelta(hours=2),
        },
    ]
    target = t0 + timedelta(hours=1, minutes=30)
    plan = PITREngine.synthesize_restore_plan(
        "db-1",
        target,
        snapshots,
        wal,
        earliest_time=t0,
        latest_time=t0 + timedelta(hours=3),
    )
    assert plan["wal_segments_to_replay"] >= 2
    assert plan.get("partial_replay") is True or plan["wal_segments_to_replay"] >= 1


def test_f2p_snapshot_restore_validates_base_backup_lsn() -> None:
    """Restore binding rejects mismatched timeline / redo LSN against WAL chain."""
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snapshots = [
        {
            "snapshot_id": "snap-bad",
            "snapshot_time": t0,
            "redo_lsn": "0/00000001",
            "timeline_id": 9,
        }
    ]
    wal = [
        {
            "timeline_id": 1,
            "sequence_number": 1,
            "start_lsn": "0/00001000",
            "end_lsn": "0/00002000",
            "start_time": t0,
            "end_time": t0 + timedelta(hours=1),
        }
    ]
    with pytest.raises(PITRWindowError):
        PITREngine.synthesize_restore_plan(
            "db-1",
            t0 + timedelta(minutes=30),
            snapshots,
            wal,
            earliest_time=t0,
            latest_time=t0 + timedelta(hours=2),
        )


def test_f2p_pitr_window_enforces_earliest_and_latest_bounds() -> None:
    """Target timestamps outside Earliest/LatestRestorableTime are rejected."""
    earliest = datetime(2024, 1, 1, tzinfo=timezone.utc)
    latest = datetime(2024, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(PITRWindowError):
        PITREngine.validate_pitr_target_window(
            datetime(2023, 12, 31, tzinfo=timezone.utc), earliest, latest
        )
    with pytest.raises(PITRWindowError):
        PITREngine.validate_pitr_target_window(
            datetime(2024, 1, 11, tzinfo=timezone.utc), earliest, latest
        )
    PITREngine.validate_pitr_target_window(
        datetime(2024, 1, 5, tzinfo=timezone.utc), earliest, latest
    )


# ---------------------------------------------------------------------------
# F2P parameter groups
# ---------------------------------------------------------------------------


def test_f2p_static_parameters_marked_pending_reboot() -> None:
    """Static apply_type parameters stay pending-reboot and are not applied immediately."""
    current = ParameterGroupManager.get_family_defaults("postgres16")
    updated, pending = ParameterGroupManager.classify_and_apply_parameters(
        "postgres16", current, {"max_connections": "250", "work_mem": "16MB"}
    )
    assert "max_connections" in pending
    assert updated.get("max_connections") == current["max_connections"]
    assert updated.get("work_mem") == "16MB"


def test_f2p_parameter_group_merges_family_defaults_and_overrides() -> None:
    """Custom overrides merge into family defaults rather than replacing the map."""
    merged = ParameterGroupManager.merge_parameter_overrides(
        "postgres16", {"work_mem": "32MB"}
    )
    assert merged["work_mem"] == "32MB"
    assert "max_connections" in merged
    assert "shared_buffers" in merged


def test_f2p_pending_reboot_cleared_only_after_boot_validation() -> None:
    """Boot validation failure must keep pending-reboot; success clears it."""
    ok, errors = ParameterGroupManager.validate_parameters_on_boot(
        "postgres16", {"max_connections": "not-an-int"}
    )
    assert ok is False
    assert errors

    async def _run() -> None:
        repo = FakeRepository()
        repo.instances["db-1"] = _base_instance(
            instance_id="db-1", pending_reboot_parameters=True
        )
        mgr = InstanceManager(repo, checkpoint_dir=Path(tempfile.mkdtemp()))
        mgr.cache_pending_static("db-1", {"max_connections": "bad"})
        with pytest.raises(Exception):
            await mgr.reboot_instance("db-1")
        assert repo.instances["db-1"]["pending_reboot_parameters"] is True

        mgr.cache_pending_static("db-1", {"max_connections": "150"})
        result = await mgr.reboot_instance("db-1")
        assert result["pending_reboot_parameters"] is False

    asyncio.run(_run())


def test_f2p_reset_parameter_group_sets_pending_reboot_status() -> None:
    """ResetDBParameterGroup marks attached instances parameter_group_status pending-reboot."""
    instances = [
        _base_instance(instance_id="db-a", parameter_group_name="custom.pg"),
        _base_instance(instance_id="db-b", parameter_group_name="other.pg"),
    ]
    marked = ParameterGroupManager.mark_instances_pending_reboot_after_reset(
        instances, "custom.pg"
    )
    by_id = {i["instance_id"]: i for i in marked}
    assert by_id["db-a"]["parameter_group_status"] == "pending-reboot"
    assert by_id["db-a"]["pending_reboot_parameters"] is True
    assert by_id["db-b"].get("parameter_group_status") != "pending-reboot" or by_id[
        "db-b"
    ].get("parameter_group_name") == "other.pg"


# ---------------------------------------------------------------------------
# F2P replica promotion
# ---------------------------------------------------------------------------


def test_f2p_replica_promotion_enforces_lag_thresholds() -> None:
    """Promotion rejects UNKNOWN status and lag above MaximumAllowedLagBytes."""
    replica = _base_instance(
        instance_id="db-rr",
        replication_status="UNKNOWN",
        replication_lag_bytes=0,
        primary_instance_id="db-primary-01",
    )
    with pytest.raises(ReplicationLagError):
        ReplicaManager.validate_replica_promotion(replica)

    replica["replication_status"] = "OK"
    replica["replication_lag_bytes"] = 50_000_000
    with pytest.raises(ReplicationLagError):
        ReplicaManager.validate_replica_promotion(replica, max_allowed_lag_bytes=10_485_760)


def test_f2p_replica_promotion_waits_for_lsn_catchup() -> None:
    """Promotion requires replica flush_lsn to catch primary write_lsn."""
    replica = _base_instance(
        instance_id="db-rr",
        replication_status="OK",
        replication_lag_bytes=0,
        primary_instance_id="db-primary-01",
        flush_lsn="0/1000000",
        replay_lsn="0/1000000",
    )
    primary = _base_instance(write_lsn="0/2000000", current_lsn="0/2000000")
    with pytest.raises(ReplicationLagError):
        ReplicaManager.validate_replica_promotion(replica, primary)


def test_f2p_replica_promotion_revokes_old_primary_write_lease() -> None:
    """Former primary write lease fields are cleared during promotion fencing."""
    primary = _base_instance()
    revoked = ReplicaManager.revoke_primary_write_lease(primary)
    assert revoked["write_lease_owner"] is None
    assert revoked["write_lease_expires_at"] is None
    assert revoked["status"] == "READ_ONLY"


def test_f2p_replica_promotion_updates_dns_routing_endpoints() -> None:
    """Endpoint switch swaps primary/replica addresses atomically on promote."""

    async def _run() -> None:
        repo = FakeRepository()
        primary = _base_instance(
            instance_id="db-primary-01",
            endpoint_address="primary.endpoint",
            write_lsn="0/2000000",
            current_lsn="0/2000000",
        )
        replica = _base_instance(
            instance_id="db-rr",
            endpoint_address="replica.endpoint",
            primary_instance_id="db-primary-01",
            replication_status="OK",
            replication_lag_bytes=0,
            flush_lsn="0/2000000",
            replay_lsn="0/2000000",
            write_lease_owner=None,
        )
        repo.instances["db-primary-01"] = primary
        repo.instances["db-rr"] = replica
        mgr = InstanceManager(repo, checkpoint_dir=Path(tempfile.mkdtemp()))
        await mgr.promote_read_replica("db-rr")
        new_primary = repo.instances["db-rr"]
        old_primary = repo.instances["db-primary-01"]
        assert new_primary["endpoint_address"] == "primary.endpoint"
        assert old_primary["endpoint_address"] == "replica.endpoint"
        # Promotion must not perform failover VIP ARP / route flush.
        assert old_primary.get("route_table_flushed") is not True
        assert old_primary.get("gratuitous_arp_sent") is not True
        assert new_primary.get("route_table_flushed") is not True
        assert new_primary.get("gratuitous_arp_sent") is not True
        assert old_primary.get("status") == "READ_ONLY"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# F2P failover
# ---------------------------------------------------------------------------


def test_f2p_failover_requires_leader_lease_acquisition() -> None:
    """Failover path acquires a leader lease with TTL before mutating VIP state."""
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    conflicting = {
        "leader_worker_id": "worker-a",
        "expires_at": now + timedelta(seconds=10),
    }
    with pytest.raises(FailoverLeaseError):
        FailoverCoordinator.acquire_leader_lease(
            "db-1",
            "worker-b",
            "10.0.0.5",
            now=now,
            ttl_sec=15,
            current_lease=conflicting,
        )
    lease = FailoverCoordinator.acquire_leader_lease(
        "db-1", "worker-a", "10.0.0.5", now=now, ttl_sec=15, current_lease=None
    )
    assert lease["leader_worker_id"] == "worker-a"
    assert lease["expires_at"] == now + timedelta(seconds=15)


def test_f2p_failover_prevents_promotion_during_valid_primary_lease() -> None:
    """Standby cannot failover while another worker holds a valid lease."""
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    current = {
        "leader_worker_id": "worker-a",
        "expires_at": now + timedelta(seconds=10),
    }
    with pytest.raises(FailoverLeaseError):
        FailoverCoordinator.validate_failover_lease("db-1", current, "worker-b", now)


def test_f2p_health_probe_distinguishes_instance_from_control_plane_lag() -> None:
    """Control-plane pool lag must not be classified as instance unreachability."""
    ok, reason = FailoverCoordinator.evaluate_health_probe(True, True)
    assert ok is True
    assert reason == "INSTANCE_HEALTHY"

    ok, reason = FailoverCoordinator.evaluate_health_probe(False, True)
    assert ok is True
    assert reason == "CONTROL_PLANE_LAG_IGNORED"

    ok, reason = FailoverCoordinator.evaluate_health_probe(False, False)
    assert ok is False


def test_f2p_vip_migration_flushes_routes_and_issues_grat_arp() -> None:
    """VIP migration evidence includes route table flush and gratuitous ARP."""
    result = FailoverCoordinator.execute_vip_migration(
        "db-1", "10.0.0.5", "10.0.0.6", "host-b"
    )
    assert result["route_table_flushed"] is True
    assert result["gratuitous_arp_sent"] is True
    assert result["status"] == "MIGRATED"


# ---------------------------------------------------------------------------
# F2P event outbox
# ---------------------------------------------------------------------------


def test_f2p_outbox_events_enqueued_transactionally() -> None:
    """Outbox enqueue happens in the same mutation path before status commit."""

    async def _run() -> None:
        repo = FakeRepository()
        repo.instances["db-1"] = _base_instance(instance_id="db-1")
        mgr = InstanceManager(repo, checkpoint_dir=Path(tempfile.mkdtemp()))
        await mgr.modify_instance("db-1", {"db_instance_class": "db.m6i.2xlarge"})
        assert len(repo.outbox) >= 1
        assert repo.outbox[0]["source_type"] == "db-instance"
        assert "create_outbox" in repo.call_order
        assert repo.call_order.index("create_outbox") < repo.call_order.index(
            "update_status:MODIFYING"
        )

    asyncio.run(_run())


def test_f2p_event_subscriptions_filter_by_source_type() -> None:
    """Subscription matching requires SourceType equality in addition to category."""
    subs = [
        {
            "subscription_id": "s1",
            "source_type": "db-instance",
            "event_category": "failover",
            "enabled": True,
        },
        {
            "subscription_id": "s2",
            "source_type": "db-snapshot",
            "event_category": "failover",
            "enabled": True,
        },
    ]
    matched = EventOutboxManager.filter_subscriptions_by_source(
        subs, "db-instance", "failover"
    )
    assert [m["subscription_id"] for m in matched] == ["s1"]


def test_f2p_event_retries_use_deterministic_identifier_hashes() -> None:
    """EventIdentifier hashes are stable across retries for the same logical event."""
    a = EventOutboxManager.generate_event_identifier(
        "db-instance", "db-1", "2024-01-01T00:00:00", "hello"
    )
    b = EventOutboxManager.generate_event_identifier(
        "db-instance", "db-1", "2024-01-01T00:00:00", "hello"
    )
    c = EventOutboxManager.generate_event_identifier(
        "db-instance", "db-1", "2024-01-01T00:00:01", "hello"
    )
    assert a == b
    assert a != c
    assert len(a) == 64

    engine = EventSubscriptionEngine()
    engine.create_subscription("s1", "100000000000", "db-instance", "failover", "http://x")
    r1 = engine.route_event_notification(
        "e1", "db-instance", "db-1", "failover", "msg", event_time="2024-01-01T00:00:00"
    )
    r2 = engine.route_event_notification(
        "e1", "db-instance", "db-1", "failover", "msg", event_time="2024-01-01T00:00:00"
    )
    assert r1["event_identifier"] == r2["event_identifier"]


def test_f2p_failed_event_deliveries_record_audit_evidence() -> None:
    """Exhausted retries mark FAILED and write event_delivery_audit evidence."""

    async def _run() -> None:
        class Cfg:
            max_event_retries = 3
            outbox_poll_interval_sec = 1

        repo = FakeRepository()
        worker = Worker(Cfg(), repo)  # type: ignore[arg-type]
        event = {
            "event_id": "evt-1",
            "source_type": "db-instance",
            "source_identifier": "db-1",
            "message": "fail me",
            "event_time": "2024-01-01T00:00:00",
        }
        if hasattr(worker, "deliver_with_retries"):
            result = await worker.deliver_with_retries(event, succeed_on_attempt=None)
            assert result["status"] == "FAILED"
            assert result["audits"]
            assert result["audits"][0]["delivery_status"] == "FAILED"
        else:
            pytest.fail("Worker.deliver_with_retries missing; delivery audit path incomplete")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# F2P checkpoints / auth / reports
# ---------------------------------------------------------------------------


def test_f2p_status_transitions_write_transaction_checkpoints() -> None:
    """Instance mutations write durable transaction checkpoints before completion."""

    async def _run() -> None:
        repo = FakeRepository()
        repo.instances["db-1"] = _base_instance(instance_id="db-1")
        chk_dir = Path(tempfile.mkdtemp())
        mgr = InstanceManager(repo, checkpoint_dir=chk_dir)
        await mgr.stop_instance("db-1")
        files = list(chk_dir.glob("*.json"))
        assert files, "expected checkpoint files after status transition"
        committed, _ = mgr.checkpoint_engine.verify_recovery_state("stop-db-1")
        assert committed is True

    asyncio.run(_run())


def test_f2p_control_plane_restart_skips_completed_operations() -> None:
    """Crash recovery skips already-committed operations to avoid duplicate side effects."""
    chk_dir = Path(tempfile.mkdtemp())
    mgr = InstanceManager(FakeRepository(), checkpoint_dir=chk_dir)
    cid = mgr.checkpoint_engine.record_operation_start("op-42", "SNAPSHOT", "db-1")
    mgr.checkpoint_engine.record_operation_commit(cid, {"status": "DONE"})
    assert mgr.should_skip_completed_operation("op-42") is True
    assert mgr.should_skip_completed_operation("op-missing") is False


def test_f2p_describe_apis_enforce_multi_tenant_isolation() -> None:
    """List/describe projections filter by account, region, and tenant_id."""
    from rds.repository import RDSRepository

    sig = inspect.signature(RDSRepository.list_instances)
    assert "tenant_id" in sig.parameters

    records = [
        _base_instance(instance_id="a", tenant_id="tenant-01"),
        _base_instance(instance_id="b", tenant_id="tenant-02"),
        _base_instance(instance_id="c", tenant_id="tenant-01", region="us-west-2"),
    ]
    filtered = AuthorizationEngine.enforce_tenant_isolation(
        records, "100000000000", "us-east-1", "tenant-01"
    )
    assert [r["instance_id"] for r in filtered] == ["a"]


def test_f2p_report_formatting_is_canonical_and_sorted() -> None:
    """Published rds-snapshot.json uses sorted keys for canonical formatting."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        report = {
            "status": "READY",
            "total_instances": 1,
            "available_instances": 1,
            "active_replicas": 0,
            "pending_events": 0,
            "instances": [
                {
                    "instance_id": "db-primary-01",
                    "status": "AVAILABLE",
                    "db_instance_class": "db.m6i.xlarge",
                    "allocated_storage_gb": 100,
                    "pending_reboot_parameters": False,
                    "multi_az": True,
                }
            ],
            "zebra": 1,
            "alpha": 2,
        }
        EvidencePublisher.publish_report(report, out)
        text = (out / "rds-snapshot.json").read_text(encoding="utf-8")
        # Sorted keys places "alpha" before "zebra" near the top-level object.
        assert text.index('"alpha"') < text.index('"zebra"')
        parsed = json.loads(text)
        assert parsed["report_digest"]
        assert (out / "instances.jsonl").is_file()
        assert (out / "events.jsonl").is_file()
        assert (out / "health.json").is_file()
        health = json.loads((out / "health.json").read_text(encoding="utf-8"))
        assert health.get("report_digest") == parsed["report_digest"]


def test_f2p_report_digest_computed_over_stable_fields() -> None:
    """Report digest is stable across equivalent payloads ignoring volatile extras."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        inst = {
            "instance_id": "db-primary-01",
            "status": "AVAILABLE",
            "db_instance_class": "db.m6i.xlarge",
            "allocated_storage_gb": 100,
            "pending_reboot_parameters": False,
            "multi_az": True,
        }
        base = {
            "status": "READY",
            "total_instances": 1,
            "available_instances": 1,
            "active_replicas": 0,
            "pending_events": 0,
            "instances": [inst],
            "zebra": 1,
            "alpha": 2,
        }
        d1 = EvidencePublisher.publish_report(dict(base, noise="a"), out)
        text = (out / "rds-snapshot.json").read_text(encoding="utf-8")
        assert text.index('"alpha"') < text.index('"zebra"')
        d2 = EvidencePublisher.publish_report(dict(base, noise="b"), out)
        assert d1 == d2
        assert len(d1) == 64


def test_f2p_readiness_status_ready_when_all_checks_pass() -> None:
    """Readiness is READY only when all instances are AVAILABLE and queues are clear."""
    healthy = [_base_instance(instance_id="db-1"), _base_instance(instance_id="db-2")]
    ready = ReadinessEvaluator.evaluate_readiness(healthy, 0, 0)
    assert ready["status"] == "READY"

    unhealthy = [_base_instance(instance_id="db-1", status="MODIFYING")]
    not_ready = ReadinessEvaluator.evaluate_readiness(unhealthy, 0, 0)
    assert not_ready["status"] == "UNHEALTHY"

    backlog = ReadinessEvaluator.evaluate_readiness(healthy, 3, 0)
    assert backlog["status"] == "UNHEALTHY"


# ---------------------------------------------------------------------------
# P2P preservation
# ---------------------------------------------------------------------------


def test_p2p_cli_entrypoint_and_api_signatures_compatible() -> None:
    """Public bin entrypoints and CLI/API signatures remain present and callable."""
    assert (RDS_HOME / "bin" / "rdsctl").exists()
    assert (RDS_HOME / "bin" / "rdsd").exists()
    assert (RDS_HOME / "bin" / "rds-worker").exists()
    ns = cli.parse_args(["health"])
    assert ns.command == "health"
    application = app_mod.create_app()
    routes = {getattr(r, "path", None) for r in application.routes}
    assert "/health" in routes
    assert "/api/v1/instances" in routes


def test_p2p_report_schema_and_migrations_preserved() -> None:
    """Migration SQL and report schema keys remain available to operators."""
    migration = RDS_HOME / "db" / "migrations" / "001_initial.sql"
    assert migration.is_file()
    sql = migration.read_text(encoding="utf-8")
    assert "event_delivery_audit" in sql
    assert "has_gap" in sql
    assert "earliest_restorable_time" in sql
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        EvidencePublisher.publish_report(
            {
                "status": "READY",
                "total_instances": 0,
                "available_instances": 0,
                "active_replicas": 0,
                "pending_events": 0,
                "instances": [],
            },
            out,
        )
        body = json.loads((out / "rds-snapshot.json").read_text(encoding="utf-8"))
        for key in (
            "status",
            "total_instances",
            "available_instances",
            "active_replicas",
            "pending_events",
            "report_digest",
            "instances",
        ):
            assert key in body


def test_p2p_offline_lab_execution_requires_no_external_aws() -> None:
    """Control-plane modules must not embed live AWS SDK / amazonaws.com calls."""
    forbidden_tokens = ("boto3", "botocore", "amazonaws.com")
    rds_pkg = RDS_HOME / "rds"
    offenders: List[str] = []
    for path in rds_pkg.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            if token in text:
                offenders.append(f"{path.name}:{token}")
    assert not offenders, f"external AWS coupling found: {offenders}"


def test_p2p_policy_violations_fail_closed_without_corruption() -> None:
    """Invalid operations raise domain errors without mutating caller-owned state."""
    records = [_base_instance(instance_id="db-1")]
    before = dict(records[0])
    with pytest.raises(AuthorizationError):
        AuthorizationEngine.authorize_single_instance(
            records[0], "999999999999", "us-east-1", "tenant-01"
        )
    assert records[0] == before

    earliest = datetime(2024, 1, 1, tzinfo=timezone.utc)
    latest = datetime(2024, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(PITRWindowError):
        PITREngine.validate_pitr_target_window(
            datetime(2024, 2, 1, tzinfo=timezone.utc), earliest, latest
        )
    assert records[0] == before
