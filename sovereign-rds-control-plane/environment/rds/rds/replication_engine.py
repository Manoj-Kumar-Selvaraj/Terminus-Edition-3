"""Streaming replication lag calculation, catch-up verifier, and endpoint switcher."""
from typing import Any, Dict, Tuple
from rds.errors import ReplicationLagError

class ReplicationEngine:
    """Manages streaming replication metrics and endpoint promotion switching."""

    @staticmethod
    def calculate_replication_lag(
        primary_lsn: str,
        replica_flush_lsn: str
    ) -> int:
        """Calculate bytes behind primary from LSN hex strings."""
        try:
            p_high, p_low = primary_lsn.split('/')
            r_high, r_low = replica_flush_lsn.split('/')

            p_bytes = (int(p_high, 16) << 32) + int(p_low, 16)
            r_bytes = (int(r_high, 16) << 32) + int(r_low, 16)

            return max(0, p_bytes - r_bytes)
        except Exception:
            return 0

    @staticmethod
    def verify_lsn_catchup(primary_lsn: str, replica_flush_lsn: str) -> Tuple[bool, int]:
        """Verify replica LSN has caught up with primary write LSN."""
        lag_bytes = ReplicationEngine.calculate_replication_lag(primary_lsn, replica_flush_lsn)
        caught_up = (lag_bytes == 0)
        return caught_up, lag_bytes

    @staticmethod
    def switch_routing_endpoints(
        primary_instance: Dict[str, Any],
        replica_instance: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Atomically switch endpoints: promoted replica becomes primary, former primary becomes read-only."""
        new_primary = dict(replica_instance)
        old_primary = dict(primary_instance)

        # Switch endpoints
        primary_endpoint = old_primary.get("endpoint_address")
        replica_endpoint = new_primary.get("endpoint_address")

        new_primary["endpoint_address"] = primary_endpoint
        new_primary["status"] = "AVAILABLE"
        new_primary["primary_instance_id"] = None
        new_primary["replication_status"] = None
        new_primary["replication_lag_bytes"] = 0

        old_primary["endpoint_address"] = replica_endpoint
        old_primary["status"] = "READ_ONLY"
        old_primary["primary_instance_id"] = new_primary["instance_id"]
        old_primary["replication_status"] = "STREAMING"

        return new_primary, old_primary
