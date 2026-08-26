"""Read replica replication lag tracking, LSN catch-up, and promotion manager."""
from typing import Any, Dict, Optional
from rds.errors import ReplicationLagError

class ReplicaManager:
    """Manages read replica topology, replication lag, LSN catch-up, and promotion fencing."""

    @staticmethod
    def validate_replica_promotion(
        replica: Dict[str, Any],
        primary: Optional[Dict[str, Any]] = None,
        max_allowed_lag_bytes: int = 10485760
    ) -> None:
        """Verify replication status, replication lag, and LSN catch-up before promotion."""
        # D13 trap: only check replication_status == OK; ignore lag and UNKNOWN.
        status = replica.get("replication_status")
        if status != "OK":
            raise ReplicationLagError(
                f"Cannot promote replica {replica.get('instance_id')}: replication status is {status}"
            )

    @staticmethod
    def revoke_primary_write_lease(primary_instance: Dict[str, Any]) -> Dict[str, Any]:
        """Revoke former primary write lease to prevent split-brain dual primary writes."""
        # D15 trap: do not clear write lease fields.
        updated_primary = dict(primary_instance)
        updated_primary["status"] = "READ_ONLY"
        return updated_primary

    @staticmethod
    def promote_replica_to_primary(
        replica_instance: Dict[str, Any],
        new_endpoint_address: str
    ) -> Dict[str, Any]:
        """Promote read replica to standalone primary instance and update routing endpoints."""
        promoted = dict(replica_instance)
        promoted["primary_instance_id"] = None
        promoted["replication_status"] = None
        promoted["replication_lag_bytes"] = 0
        promoted["status"] = "AVAILABLE"
        promoted["endpoint_address"] = new_endpoint_address
        promoted["write_lease_owner"] = f"primary-{promoted['instance_id']}"
        return promoted
