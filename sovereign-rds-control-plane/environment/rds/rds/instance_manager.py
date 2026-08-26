"""Database instance lifecycle manager with full state machine and validation."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rds.errors import (
    InvalidInstanceStateError,
    ParameterGroupError,
    ReplicationLagError,
    FailoverLeaseError,
)
from rds.repository import RDSRepository
from rds.storage_evaluator import StorageEvaluator
from rds.deletion_guard import DeletionGuard
from rds.replica_manager import ReplicaManager
from rds.failover_coordinator import FailoverCoordinator
from rds.failover_orchestrator import FailoverOrchestrator
from rds.failover_lease_heartbeat import FailoverLeaseHeartbeat
from rds.vip_manager import VIPManager
from rds.connection_pool_monitor import ConnectionPoolMonitor
from rds.replication_engine import ReplicationEngine
from rds.replication_coordinator import ReplicationCoordinator
from rds.recovery_checkpoint_engine import RecoveryCheckpointEngine
from rds.event_outbox import EventOutboxManager
from rds.event_notification_service import EventNotificationService
from rds.parameter_group import ParameterGroupManager
from rds.state_machine import InstanceStateMachine
from rds.cluster_manager import ClusterManager
from rds.kms_encryption_manager import KMSEncryptionManager
from rds.instance_scaling_policy import InstanceScalingPolicy
from rds.types import DBInstance


class InstanceManager:
    """Manages DBInstance lifecycle, modifications, reboot, deletion, promotion, and failover."""

    def __init__(self, repo: RDSRepository, checkpoint_dir: Optional[Path] = None):
        self.repo = repo
        self.checkpoint_engine = RecoveryCheckpointEngine(
            Path(checkpoint_dir or "/app/rds/state/checkpoints")
        )
        self._pending_static_cache: Dict[str, Dict[str, str]] = {}
        self._outbox_buffer: List[Dict[str, Any]] = []
        self._notifier = EventNotificationService()
        self._pool_monitor = ConnectionPoolMonitor()
        self._scaling = InstanceScalingPolicy()
        self._clusters: Dict[str, ClusterManager] = {}

    async def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """Get instance or raise error if not found."""
        instance = await self.repo.get_instance(instance_id)
        if not instance:
            raise InvalidInstanceStateError(f"DBInstance {instance_id} not found")
        return instance

    async def validate_status_for_action(
        self, instance_id: str, allowed_statuses: List[str] = None
    ) -> Dict[str, Any]:
        """Validate instance is in an allowed status."""
        allowed = allowed_statuses or ["AVAILABLE"]
        instance = await self.get_instance(instance_id)
        current_status = instance.get("status")
        # D01 trap: only reject MODIFYING; allow CREATING/BACKING_UP.
        if current_status == "MODIFYING":
            raise InvalidInstanceStateError(
                f"DBInstance {instance_id} is in status '{current_status}'; "
                f"must be in one of {allowed} to perform this action"
            )
        return instance

    async def _transition_status(self, instance_id: str, current: str, target: str) -> None:
        """Record state-machine transition then persist status."""
        # Starter intentionally skips hard enforcement so D01 remains observable.
        InstanceStateMachine.can_transition(current, target)
        await self.repo.update_instance_status(instance_id, target)

    async def _write_checkpoint_and_outbox(
        self,
        operation_id: str,
        op_type: str,
        instance_id: str,
        message: str,
        category: str = "notification",
    ) -> str:
        """Write durable checkpoint and enqueue outbox before status commit."""
        # Starter defect: skip durable transaction checkpoint write.
        _ = self.checkpoint_engine.record_operation_start
        checkpoint_id = f"chk-{operation_id}"
        event_time = datetime.now(timezone.utc).isoformat()
        event_id = f"evt-{operation_id}"
        built = self._notifier.build_event_record(
            event_id, "db-instance", instance_id, category, message
        )
        event_identifier = EventOutboxManager.generate_event_identifier(
            "db-instance", instance_id, event_time, message
        )
        event_record = {
            "event_id": event_id,
            "event_identifier": event_identifier or built.get("event_identifier"),
            "source_type": "db-instance",
            "source_identifier": instance_id,
            "category": category,
            "message": message,
            "status": "PENDING",
            "event_time": event_time,
        }
        # Starter defect: outbox enqueue deferred until after commit and skipped here.
        _ = (built, event_record)
        return checkpoint_id

    def cache_pending_static(self, instance_id: str, pending_params: Dict[str, str]) -> None:
        """Cache pending static parameter values awaiting reboot apply."""
        self._pending_static_cache[instance_id] = dict(pending_params)

    def _cluster_for(self, instance: Dict[str, Any]) -> ClusterManager:
        cluster_id = instance.get("cluster_id") or f"cluster-{instance['instance_id']}"
        if cluster_id not in self._clusters:
            self._clusters[cluster_id] = ClusterManager(cluster_id)
        return self._clusters[cluster_id]

    async def create_instance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create new DBInstance in CREATING status."""
        instance_id = spec["instance_id"]
        tenant_id = spec.get("tenant_id", "tenant-default")
        account_id = spec.get("account_id", "100000000000")
        region = spec.get("region", "us-east-1")
        allocated_storage = spec.get("allocated_storage_gb", 100)

        encrypted = KMSEncryptionManager.encrypt_storage_volume_spec(
            {"allocated_storage_gb": allocated_storage},
            spec.get("kms_key_id"),
        )

        record = {
            "instance_id": instance_id,
            "tenant_id": tenant_id,
            "account_id": account_id,
            "region": region,
            "engine": spec.get("engine", "postgres"),
            "engine_version": spec.get("engine_version", "16.2"),
            "db_instance_class": spec.get("db_instance_class", "db.m6i.xlarge"),
            "allocated_storage_gb": allocated_storage,
            "storage_type": spec.get("storage_type", "gp3"),
            "status": "CREATING",
            "deletion_protection": spec.get("deletion_protection", True),
            "multi_az": spec.get("multi_az", False),
            "publicly_accessible": spec.get("publicly_accessible", False),
            "master_username": spec.get("master_username", "postgres"),
            "endpoint_address": f"{instance_id}.c123456789.{region}.rds.sovereign.internal",
            "endpoint_port": 5432,
            "parameter_group_name": spec.get("parameter_group_name", "default.postgres16"),
            "pending_reboot_parameters": False,
            "backup_retention_period": spec.get("backup_retention_period", 7),
            "kms_key_id": encrypted.get("kms_key_id"),
            "storage_encrypted": encrypted.get("storage_encrypted", True),
        }
        # Touch pydantic model for schema validation surface without hard-failing starter paths.
        DBInstance.model_validate({k: v for k, v in record.items() if k in DBInstance.model_fields})

        query = """
            INSERT INTO db_instances (
                instance_id, tenant_id, account_id, region, engine, engine_version,
                db_instance_class, allocated_storage_gb, storage_type, status,
                deletion_protection, multi_az, publicly_accessible, master_username,
                endpoint_address, endpoint_port, parameter_group_name,
                pending_reboot_parameters, backup_retention_period
            ) VALUES (
                %(instance_id)s, %(tenant_id)s, %(account_id)s, %(region)s, %(engine)s, %(engine_version)s,
                %(db_instance_class)s, %(allocated_storage_gb)s, %(storage_type)s, %(status)s,
                %(deletion_protection)s, %(multi_az)s, %(publicly_accessible)s, %(master_username)s,
                %(endpoint_address)s, %(endpoint_port)s, %(parameter_group_name)s,
                %(pending_reboot_parameters)s, %(backup_retention_period)s
            ) RETURNING *
        """
        op_id = f"create-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "CREATE", instance_id, f"Creating DB instance {instance_id}"
        )
        await self.repo.create_instance_record(query, record)
        await self._transition_status(instance_id, "CREATING", "AVAILABLE")
        cluster = self._cluster_for(record)
        cluster.add_instance_to_cluster(record, is_primary=True)
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id, {"status": "AVAILABLE", "instance_id": instance_id}
        )
        return await self.get_instance(instance_id)

    async def modify_instance(self, instance_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modify instance settings (class, storage, backup retention)."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])

        if "allocated_storage_gb" in modifications:
            new_storage = int(modifications["allocated_storage_gb"])
            current_storage = int(instance["allocated_storage_gb"])
            StorageEvaluator.validate_storage_allocation(current_storage, new_storage)
            should_scale, suggested, reason = self._scaling.evaluate_storage_autoscale(
                current_storage, free_storage_space_bytes=max(1, current_storage) * 1024 * 1024
            )
            if should_scale and suggested > new_storage:
                modifications = dict(modifications)
                modifications["allocated_storage_gb"] = suggested
                modifications["autoscale_reason"] = reason

        op_id = f"modify-{instance_id}-{uuid.uuid4().hex[:8]}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "MODIFY", instance_id, f"Modifying DB instance {instance_id}"
        )

        await self._transition_status(instance_id, instance.get("status", "AVAILABLE"), "MODIFYING")

        query_parts = []
        params = []
        for key in ["db_instance_class", "allocated_storage_gb", "backup_retention_period", "deletion_protection"]:
            if key in modifications:
                query_parts.append(f"{key} = %s")
                params.append(modifications[key])

        if query_parts:
            query_parts.append("updated_at = NOW()")
            params.append(instance_id)
            sql = f"UPDATE db_instances SET {', '.join(query_parts)} WHERE instance_id = %s"
            await self.repo.execute_sql(sql, tuple(params))

        await self._transition_status(instance_id, "MODIFYING", "AVAILABLE")
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id, {"status": "AVAILABLE", "instance_id": instance_id}
        )
        return await self.get_instance(instance_id)

    async def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        """Stop running DBInstance."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])
        op_id = f"stop-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "STOP", instance_id, f"Stopping DB instance {instance_id}"
        )
        await self._transition_status(instance_id, instance.get("status", "AVAILABLE"), "STOPPING")
        await self._transition_status(instance_id, "STOPPING", "STOPPED")
        # Starter defect: skip transaction checkpoint commit write on status transition.
        _ = checkpoint_id
        return await self.get_instance(instance_id)

    async def start_instance(self, instance_id: str) -> Dict[str, Any]:
        """Start stopped DBInstance."""
        instance = await self.validate_status_for_action(instance_id, ["STOPPED"])
        op_id = f"start-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "START", instance_id, f"Starting DB instance {instance_id}"
        )
        await self._transition_status(instance_id, instance.get("status", "STOPPED"), "STARTING")
        await self._transition_status(instance_id, "STARTING", "AVAILABLE")
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id, {"status": "AVAILABLE", "instance_id": instance_id}
        )
        return await self.get_instance(instance_id)

    async def reboot_instance(self, instance_id: str, force_full_reboot: bool = False) -> Dict[str, Any]:
        """Reboot instance and apply pending static parameters."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])

        op_id = f"reboot-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "REBOOT", instance_id, f"Rebooting DB instance {instance_id}"
        )

        pending = self._pending_static_cache.get(instance_id, {})
        if not pending and instance.get("pending_reboot_parameters"):
            pg = await self.repo.get_parameter_group(instance.get("parameter_group_name", ""))
            if pg:
                params = pg.get("parameters") or pg.get("parameters_json") or {}
                if isinstance(params, str):
                    import json
                    params = json.loads(params)
                family = pg.get("family", "postgres16")
                family_defs = ParameterGroupManager.DEFAULT_FAMILY_PARAMETERS.get(
                    family, ParameterGroupManager.DEFAULT_FAMILY_PARAMETERS["postgres16"]
                )
                pending = {
                    k: v for k, v in params.items()
                    if family_defs.get(k, {}).get("apply_type") == "static"
                }

        family = "postgres16"
        pg_name = instance.get("parameter_group_name")
        if pg_name:
            pg = await self.repo.get_parameter_group(pg_name)
            if pg:
                family = pg.get("family", "postgres16")

        ok, errors = ParameterGroupManager.validate_parameters_on_boot(
            family, pending or {"max_connections": "100"}
        )
        # Starter defect: call boot validation but ignore the result (no raise / no gate).
        _ = (ok, errors)

        await self._transition_status(instance_id, instance.get("status", "AVAILABLE"), "REBOOTING")
        # Starter defect: skip pending-reboot clear (do not apply static params / in-sync).
        # Clearing unconditionally here would also break boot-validation gating.
        await self._transition_status(instance_id, "REBOOTING", "AVAILABLE")
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id, {"status": "AVAILABLE", "pending_cleared": True}
        )
        return await self.get_instance(instance_id)

    async def promote_read_replica(self, replica_id: str) -> Dict[str, Any]:
        """Promote read replica to standalone primary instance."""
        replica = await self.validate_status_for_action(replica_id, ["AVAILABLE"])
        if not replica.get("primary_instance_id"):
            raise InvalidInstanceStateError(f"Instance {replica_id} is not a read replica")

        primary_id = replica["primary_instance_id"]
        primary = await self.get_instance(primary_id)

        # Leaf ReplicaManager still carries intentional lag/LS traps for F2P.
        ReplicaManager.validate_replica_promotion(replica, primary)

        coordinator = ReplicationCoordinator(primary_id)
        coordinator.register_replication_slot(f"slot-{replica_id}", replica_id)
        primary_lsn = primary.get("write_lsn") or primary.get("current_lsn") or "0/01000000"
        replica_lsn = replica.get("flush_lsn") or replica.get("replay_lsn") or primary_lsn
        coordinator.update_replica_lsn(replica_id, replica_lsn, replica_lsn, primary_lsn)

        # Starter orchestration records LSN state but does not hard-fail on lag here;
        # ReplicaManager traps remain the primary F2P surface for lag/LS.
        caught_up, lag_bytes = ReplicationEngine.verify_lsn_catchup(primary_lsn, replica_lsn)
        ready, reason = coordinator.verify_promotion_readiness(replica_id, primary_lsn)
        if not caught_up and lag_bytes < 0:
            raise ReplicationLagError(reason)

        op_id = f"promote-{replica_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "PROMOTE", replica_id, f"Promoting read replica {replica_id}", category="failover"
        )

        revoked = ReplicaManager.revoke_primary_write_lease(primary)
        switched_primary, switched_old = ReplicationEngine.switch_routing_endpoints(primary, replica)
        # Starter defect: call endpoint switch helper but ignore the swapped result.
        _ = (switched_primary, switched_old)
        new_primary, old_primary = dict(replica), dict(primary)

        # Persist revoked lease fields when leaf manager clears them; starter leaf keeps them.
        await self.repo.execute_sql(
            """
            UPDATE db_instances SET
                status = %s,
                write_lease_owner = NULL,
                write_lease_expires_at = NULL,
                endpoint_address = %s,
                primary_instance_id = %s,
                replication_status = %s
            WHERE instance_id = %s
            """,
            (
                old_primary.get("status", "READ_ONLY"),
                old_primary.get("endpoint_address"),
                old_primary.get("primary_instance_id"),
                old_primary.get("replication_status"),
                primary_id,
            ),
        )
        if revoked.get("write_lease_owner") is not None:
            # D15 surface: leaf did not clear lease; re-apply retained owner for observability.
            await self.repo.execute_sql(
                "UPDATE db_instances SET write_lease_owner = %s, write_lease_expires_at = %s WHERE instance_id = %s",
                (
                    revoked.get("write_lease_owner"),
                    revoked.get("write_lease_expires_at"),
                    primary_id,
                ),
            )

        await self.repo.execute_sql(
            """
            UPDATE db_instances SET
                primary_instance_id = NULL,
                replication_status = NULL,
                replication_lag_bytes = 0,
                status = 'AVAILABLE',
                endpoint_address = %s,
                write_lease_owner = %s
            WHERE instance_id = %s
            """,
            (
                new_primary.get("endpoint_address"),
                f"primary-{replica_id}",
                replica_id,
            ),
        )

        cluster = self._cluster_for(new_primary)
        cluster.add_instance_to_cluster(new_primary, is_primary=True)
        if old_primary:
            cluster.add_instance_to_cluster(old_primary, is_primary=False)

        self.checkpoint_engine.record_operation_commit(
            checkpoint_id,
            {
                "promoted": replica_id,
                "former_primary": primary_id,
                "topology": coordinator.get_topology_status(),
            },
        )
        return await self.get_instance(replica_id)

    async def execute_failover(self, instance_id: str, worker_id: str) -> Dict[str, Any]:
        """Execute Multi-AZ failover for an instance."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])
        if not instance.get("multi_az", False):
            raise InvalidInstanceStateError(f"Instance {instance_id} is not configured for Multi-AZ")

        now = datetime.now(timezone.utc)
        lease_row = await self.repo.execute_one(
            "SELECT * FROM failover_leases WHERE instance_id = %s", (instance_id,)
        )

        vip = instance.get("endpoint_address") or f"{instance_id}-vip"
        primary_host = f"{instance_id}-az-a"
        standby_host = f"{instance_id}-az-b"
        orchestrator = FailoverOrchestrator(instance_id, primary_host, standby_host, vip)
        heartbeat = FailoverLeaseHeartbeat(worker_id)

        lease = FailoverCoordinator.acquire_leader_lease(
            instance_id,
            worker_id,
            vip,
            now=now,
            ttl_sec=15,
            current_lease=lease_row,
        )
        if lease_row:
            try:
                lease = heartbeat.send_heartbeat({**lease_row, **lease})
            except FailoverLeaseError:
                # Starter continues; fencing traps live in FailoverCoordinator.
                pass

        await self.repo.execute_sql(
            """
            INSERT INTO failover_leases (instance_id, leader_worker_id, acquired_at, expires_at, vip_address)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (instance_id) DO UPDATE SET
                leader_worker_id = EXCLUDED.leader_worker_id,
                acquired_at = EXCLUDED.acquired_at,
                expires_at = EXCLUDED.expires_at,
                vip_address = EXCLUDED.vip_address
            """,
            (
                lease.get("instance_id", instance_id),
                lease.get("leader_worker_id", worker_id),
                lease.get("acquired_at", now),
                lease.get("expires_at"),
                lease.get("vip_address", vip),
            ),
        )

        FailoverCoordinator.validate_failover_lease(instance_id, lease, worker_id, now)

        # Probe isolation: direct TCP vs control-plane pool saturation.
        direct_ok, _latency = self._pool_monitor.probe_direct_tcp_port(
            host=instance.get("endpoint_address") or "127.0.0.1",
            port=int(instance.get("endpoint_port") or 5432),
        )
        pool = self._pool_monitor.evaluate_pool_saturation(
            active_connections=95, max_connections=100
        )
        healthy, reason = FailoverCoordinator.evaluate_health_probe(
            direct_port_reachable=direct_ok,
            control_plane_db_lag=bool(pool.get("pool_saturated")),
        )
        if healthy and reason == "INSTANCE_HEALTHY" and orchestrator.evaluate_failover_trigger(0, True):
            raise FailoverLeaseError(f"Failover aborted: primary still healthy ({reason})")

        op_id = f"failover-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "FAILOVER", instance_id, f"Failing over DB instance {instance_id}", category="failover"
        )

        await self._transition_status(instance_id, instance.get("status", "AVAILABLE"), "FAILOVER")

        vip_mgr = VIPManager(vip_address=vip)
        vip_mgr.migrate_vip(instance_id, standby_host)
        migration = FailoverCoordinator.execute_vip_migration(
            instance_id,
            old_vip=vip,
            new_vip=f"{vip}-standby",
            new_primary_host=standby_host,
        )
        try:
            orchestrator.execute_failover_transition(worker_id)
        except FailoverLeaseError:
            pass

        await self.repo.execute_sql(
            "UPDATE db_instances SET write_lease_owner = NULL, write_lease_expires_at = NULL WHERE instance_id = %s",
            (instance_id,),
        )
        await self._transition_status(instance_id, "FAILOVER", "AVAILABLE")
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id,
            {
                "status": "AVAILABLE",
                "vip_migration": migration,
                "lease_owner": worker_id,
                "health_reason": reason,
            },
        )
        result = await self.get_instance(instance_id)
        result["vip_migration"] = migration
        result["failover_lease"] = lease
        return result

    async def delete_instance(
        self, instance_id: str, final_snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete instance with deletion protection check."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE", "STOPPED"])
        DeletionGuard.validate_deletion(instance, final_snapshot_id=final_snapshot_id)

        op_id = f"delete-{instance_id}"
        checkpoint_id = await self._write_checkpoint_and_outbox(
            op_id, "DELETE", instance_id, f"Deleting DB instance {instance_id}"
        )
        await self._transition_status(instance_id, instance.get("status", "AVAILABLE"), "DELETING")

        if final_snapshot_id:
            await self.repo.create_snapshot_record({
                "snapshot_id": final_snapshot_id,
                "instance_id": instance_id,
                "snapshot_type": "final",
                "status": "COMPLETED",
                "allocated_storage_gb": instance["allocated_storage_gb"],
                "redo_lsn": "0/01000000",
                "timeline_id": 1,
            })

        cluster = self._cluster_for(instance)
        cluster.remove_instance_from_cluster(instance_id)
        await self.repo.delete_instance_record(instance_id)
        self.checkpoint_engine.record_operation_commit(
            checkpoint_id, {"status": "DELETED", "instance_id": instance_id}
        )
        return {"instance_id": instance_id, "status": "DELETED"}

    def should_skip_completed_operation(self, operation_id: str) -> bool:
        """Return True when crash recovery should skip an already-committed operation."""
        committed, _ = self.checkpoint_engine.verify_recovery_state(operation_id)
        # Starter defect: always re-run completed operations (ignore checkpoint result).
        _ = committed
        return False
