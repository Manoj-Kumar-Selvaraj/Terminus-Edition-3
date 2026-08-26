"""Read replica replication lag tracking, LSN catch-up, and promotion manager."""
from typing import Any, Dict, Optional
from rds.errors import ReplicationLagError
from rds.replication_engine import ReplicationEngine


class ReplicaManager:
    """Manages read replica topology, replication lag, LSN catch-up, and promotion fencing."""

    @staticmethod
    def validate_replica_promotion(
        replica: Dict[str, Any],
        primary: Optional[Dict[str, Any]] = None,
        max_allowed_lag_bytes: int = 10485760
    ) -> None:
        """Verify replication status, replication lag, and LSN catch-up before promotion."""
        lag = replica.get("replication_lag_bytes", 0)
        status = replica.get("replication_status")

        if status == "UNKNOWN" or lag is None or lag > max_allowed_lag_bytes:
            raise ReplicationLagError(
                f"Cannot promote replica {replica.get('instance_id')}: replication lag ({lag} bytes) "
                f"exceeds maximum allowed lag ({max_allowed_lag_bytes} bytes) or status is UNKNOWN"
            )

        if primary is not None:
            primary_lsn = primary.get("write_lsn") or primary.get("current_lsn") or "0/0"
            replica_lsn = replica.get("flush_lsn") or replica.get("replay_lsn") or "0/0"
            caught_up, lag_bytes = ReplicationEngine.verify_lsn_catchup(primary_lsn, replica_lsn)
            if not caught_up:
                raise ReplicationLagError(
                    f"Cannot promote replica {replica.get('instance_id')}: "
                    f"flush_lsn lag {lag_bytes} bytes behind primary write_lsn"
                )

    @staticmethod
    def revoke_primary_write_lease(primary_instance: Dict[str, Any]) -> Dict[str, Any]:
        """Revoke former primary write lease to prevent split-brain dual primary writes."""
        updated_primary = dict(primary_instance)
        updated_primary["write_lease_owner"] = None
        updated_primary["write_lease_expires_at"] = None
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
