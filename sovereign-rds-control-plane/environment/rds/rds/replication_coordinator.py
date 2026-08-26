"""Streaming replication slot manager, LSN catch-up calculator, and cascading replica router."""
from typing import Any, Dict, List, Optional, Tuple
from rds.errors import ReplicationLagError
from rds.wal_collector import WALCollector

class ReplicationCoordinator:
    """Coordinates streaming replication slots, lag tracking, and cascading replica topologies."""

    def __init__(self, primary_instance_id: str, max_allowed_lag_bytes: int = 10485760):
        self.primary_instance_id = primary_instance_id
        self.max_allowed_lag_bytes = max_allowed_lag_bytes
        self.replication_slots: Dict[str, Dict[str, Any]] = {}
        self.replicas: Dict[str, Dict[str, Any]] = {}

    def register_replication_slot(self, slot_name: str, replica_instance_id: str) -> Dict[str, Any]:
        """Register a new replication slot for a read replica."""
        slot = {
            "slot_name": slot_name,
            "replica_instance_id": replica_instance_id,
            "primary_instance_id": self.primary_instance_id,
            "active": True,
            "confirmed_flush_lsn": "0/01000000",
            "restart_lsn": "0/01000000",
        }
        self.replication_slots[slot_name] = slot
        return slot

    def update_replica_lsn(
        self,
        replica_id: str,
        write_lsn: str,
        flush_lsn: str,
        primary_write_lsn: str
    ) -> Dict[str, Any]:
        """Update LSN status for a replica and calculate replication lag in bytes."""
        primary_lsn_val = WALCollector.parse_lsn(primary_write_lsn)
        replica_flush_val = WALCollector.parse_lsn(flush_lsn)

        lag_bytes = max(0, primary_lsn_val - replica_flush_val)
        status = "STREAMING" if lag_bytes <= self.max_allowed_lag_bytes else "LAGGING"

        info = {
            "replica_id": replica_id,
            "write_lsn": write_lsn,
            "flush_lsn": flush_lsn,
            "primary_write_lsn": primary_write_lsn,
            "replication_lag_bytes": lag_bytes,
            "status": status,
        }
        self.replicas[replica_id] = info
        return info

    def verify_promotion_readiness(self, replica_id: str, primary_write_lsn: str) -> Tuple[bool, str]:
        """Verify replica is caught up and ready for promotion."""
        info = self.replicas.get(replica_id)
        if not info:
            return False, f"Replica {replica_id} not found in replication coordinator"

        lag = info.get("replication_lag_bytes", 99999999)
        if lag > self.max_allowed_lag_bytes:
            return False, f"Replica {replica_id} lag ({lag} bytes) exceeds maximum allowed ({self.max_allowed_lag_bytes} bytes)"

        flush_val = WALCollector.parse_lsn(info.get("flush_lsn", "0/0"))
        primary_val = WALCollector.parse_lsn(primary_write_lsn)

        if flush_val < primary_val:
            return False, f"Replica {replica_id} flush LSN ({info.get('flush_lsn')}) behind primary LSN ({primary_write_lsn})"

        return True, "READY_FOR_PROMOTION"

    def get_topology_status(self) -> Dict[str, Any]:
        """Get summary of replication topology health."""
        total = len(self.replicas)
        streaming = sum(1 for r in self.replicas.values() if r.get("status") == "STREAMING")

        return {
            "primary_instance_id": self.primary_instance_id,
            "total_replicas": total,
            "streaming_replicas": streaming,
            "lagging_replicas": total - streaming,
            "active_slots": len([s for s in self.replication_slots.values() if s.get("active")]),
        }
