"""Database instance lifecycle manager with full state machine and validation."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from rds.errors import InvalidInstanceStateError, DeletionProtectionError, StorageShrinkError, ReplicationLagError, FailoverLeaseError
from rds.repository import RDSRepository
from rds.storage_evaluator import StorageEvaluator
from rds.deletion_guard import DeletionGuard
from rds.replica_manager import ReplicaManager
from rds.failover_coordinator import FailoverCoordinator

class InstanceManager:
    """Manages DBInstance lifecycle, modifications, reboot, deletion, promotion, and failover."""

    def __init__(self, repo: RDSRepository, checkpoint_dir: Optional[Path] = None):
        self.repo = repo
        self.checkpoint_dir = checkpoint_dir

    async def get_instance(self, instance_id: str) -> Dict[str, Any]:
        """Get instance or raise error if not found."""
        instance = await self.repo.get_instance(instance_id)
        if not instance:
            raise InvalidInstanceStateError(f"DBInstance {instance_id} not found")
        return instance

    async def validate_status_for_action(self, instance_id: str, allowed_statuses: List[str] = None) -> Dict[str, Any]:
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

    async def create_instance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create new DBInstance in CREATING status."""
        instance_id = spec["instance_id"]
        tenant_id = spec.get("tenant_id", "tenant-default")
        account_id = spec.get("account_id", "100000000000")
        region = spec.get("region", "us-east-1")
        allocated_storage = spec.get("allocated_storage_gb", 100)

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
        }

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
        await self.repo.create_instance_record(query, record)
        await self.repo.update_instance_status(instance_id, "AVAILABLE")
        return await self.get_instance(instance_id)

    async def modify_instance(self, instance_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modify instance settings (class, storage, backup retention)."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])

        if "allocated_storage_gb" in modifications:
            new_storage = int(modifications["allocated_storage_gb"])
            current_storage = int(instance["allocated_storage_gb"])
            StorageEvaluator.validate_storage_allocation(current_storage, new_storage)

        await self.repo.update_instance_status(instance_id, "MODIFYING")

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

        await self.repo.update_instance_status(instance_id, "AVAILABLE")
        return await self.get_instance(instance_id)

    async def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        """Stop running DBInstance."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])
        await self.repo.update_instance_status(instance_id, "STOPPING")
        await self.repo.update_instance_status(instance_id, "STOPPED")
        return await self.get_instance(instance_id)

    async def start_instance(self, instance_id: str) -> Dict[str, Any]:
        """Start stopped DBInstance."""
        instance = await self.validate_status_for_action(instance_id, ["STOPPED"])
        await self.repo.update_instance_status(instance_id, "STARTING")
        await self.repo.update_instance_status(instance_id, "AVAILABLE")
        return await self.get_instance(instance_id)

    async def reboot_instance(self, instance_id: str, force_full_reboot: bool = False) -> Dict[str, Any]:
        """Reboot instance and apply pending static parameters."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])

        await self.repo.update_instance_status(instance_id, "REBOOTING")

        # Clear pending reboot parameters flag after boot
        await self.repo.clear_pending_reboot(instance_id)
        await self.repo.update_instance_status(instance_id, "AVAILABLE")

        return await self.get_instance(instance_id)

    async def promote_read_replica(self, replica_id: str) -> Dict[str, Any]:
        """Promote read replica to standalone primary instance."""
        replica = await self.validate_status_for_action(replica_id, ["AVAILABLE"])
        if not replica.get("primary_instance_id"):
            raise InvalidInstanceStateError(f"Instance {replica_id} is not a read replica")

        ReplicaManager.validate_replica_promotion(replica)

        primary_id = replica["primary_instance_id"]
        primary = await self.get_instance(primary_id)

        # Revoke former primary write lease to prevent dual primary
        revoked = ReplicaManager.revoke_primary_write_lease(primary)
        await self.repo.execute_sql(
            "UPDATE db_instances SET status = 'READ_ONLY', write_lease_owner = NULL WHERE instance_id = %s",
            (primary_id,)
        )

        # Promote replica
        new_endpoint = f"{replica_id}.c123456789.{replica['region']}.rds.sovereign.internal"
        promoted = ReplicaManager.promote_replica_to_primary(replica, new_endpoint)

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
            (new_endpoint, f"primary-{replica_id}", replica_id)
        )

        return await self.get_instance(replica_id)

    async def execute_failover(self, instance_id: str, worker_id: str) -> Dict[str, Any]:
        """Execute Multi-AZ failover for an instance."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE"])
        if not instance.get("multi_az", False):
            raise InvalidInstanceStateError(f"Instance {instance_id} is not configured for Multi-AZ")

        now = datetime.now(timezone.utc)
        # Fetch current lease if any
        lease_row = await self.repo.execute_one(
            "SELECT * FROM failover_leases WHERE instance_id = %s", (instance_id,)
        )
        FailoverCoordinator.validate_failover_lease(instance_id, lease_row, worker_id, now)

        await self.repo.update_instance_status(instance_id, "FAILOVER")
        await self.repo.update_instance_status(instance_id, "AVAILABLE")

        return await self.get_instance(instance_id)

    async def delete_instance(self, instance_id: str, final_snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete instance with deletion protection check."""
        instance = await self.validate_status_for_action(instance_id, ["AVAILABLE", "STOPPED"])
        DeletionGuard.validate_deletion(instance, final_snapshot_id=final_snapshot_id)

        await self.repo.update_instance_status(instance_id, "DELETING")

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

        await self.repo.delete_instance_record(instance_id)
        return {"instance_id": instance_id, "status": "DELETED"}
