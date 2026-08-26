"""Database cluster topology, reader load-balancing pool, and primary endpoint router."""
from typing import Any, Dict, List, Optional
from rds.errors import InvalidInstanceStateError

class ClusterManager:
    """Manages Aurora-style multi-instance cluster topology and endpoints."""

    def __init__(self, cluster_id: str):
        self.cluster_id = cluster_id
        self.members: Dict[str, Dict[str, Any]] = {}
        self.primary_id: Optional[str] = None
        self.reader_ids: List[str] = []

    def add_instance_to_cluster(
        self,
        instance: Dict[str, Any],
        is_primary: bool = False
    ) -> Dict[str, Any]:
        """Add DBInstance member to cluster."""
        inst_id = instance["instance_id"]
        self.members[inst_id] = instance

        if is_primary:
            if self.primary_id and self.primary_id != inst_id:
                # Demote old primary to reader
                self.reader_ids.append(self.primary_id)
            self.primary_id = inst_id
            if inst_id in self.reader_ids:
                self.reader_ids.remove(inst_id)
        else:
            if inst_id not in self.reader_ids and inst_id != self.primary_id:
                self.reader_ids.append(inst_id)

        return self.get_cluster_endpoints()

    def remove_instance_from_cluster(self, instance_id: str) -> None:
        """Remove DBInstance from cluster topology."""
        if instance_id in self.members:
            del self.members[instance_id]
        if instance_id == self.primary_id:
            self.primary_id = None
        if instance_id in self.reader_ids:
            self.reader_ids.remove(instance_id)

    def get_cluster_endpoints(self) -> Dict[str, Any]:
        """Get primary writer endpoint and reader load-balanced endpoints."""
        primary_inst = self.members.get(self.primary_id) if self.primary_id else None
        primary_endpoint = primary_inst.get("endpoint_address") if primary_inst else None

        reader_endpoints = [
            self.members[rid].get("endpoint_address")
            for rid in self.reader_ids
            if rid in self.members and self.members[rid].get("endpoint_address")
        ]

        return {
            "cluster_id": self.cluster_id,
            "primary_instance_id": self.primary_id,
            "writer_endpoint": primary_endpoint,
            "reader_count": len(self.reader_ids),
            "reader_endpoints": reader_endpoints,
            "total_members": len(self.members),
        }

    def select_failover_candidate(self) -> Optional[Dict[str, Any]]:
        """Select best reader instance candidate for failover promotion."""
        if not self.reader_ids:
            return None

        candidates = [
            self.members[rid] for rid in self.reader_ids
            if rid in self.members and self.members[rid].get("status") == "AVAILABLE"
        ]

        if not candidates:
            return None

        # Select candidate with lowest replication lag
        return min(candidates, key=lambda x: x.get("replication_lag_bytes", 0))
