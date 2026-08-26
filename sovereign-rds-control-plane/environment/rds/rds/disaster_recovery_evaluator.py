"""Disaster Recovery (DR) evaluator, RPO/RTO calculator, and cross-region replication monitor."""
from datetime import datetime, timezone
from typing import Any, Dict, List

class DisasterRecoveryEvaluator:
    """Evaluates cross-region replication health, RPO/RTO compliance, and DR readiness."""

    def __init__(self, target_rpo_seconds: int = 300, target_rto_seconds: int = 900):
        self.target_rpo_seconds = target_rpo_seconds
        self.target_rto_seconds = target_rto_seconds

    def evaluate_rpo_compliance(
        self,
        replication_lag_bytes: int,
        bytes_per_second_write_rate: int = 1048576  # 1 MB/s
    ) -> Dict[str, Any]:
        """Calculate estimated RPO lag in seconds from replication lag bytes."""
        if bytes_per_second_write_rate <= 0:
            estimated_rpo_sec = 0.0
        else:
            estimated_rpo_sec = round(replication_lag_bytes / float(bytes_per_second_write_rate), 2)

        rpo_compliant = estimated_rpo_sec <= self.target_rpo_seconds

        return {
            "replication_lag_bytes": replication_lag_bytes,
            "estimated_rpo_seconds": estimated_rpo_sec,
            "target_rpo_seconds": self.target_rpo_seconds,
            "rpo_compliant": rpo_compliant,
        }

    def evaluate_dr_readiness(
        self,
        primary_instance: Dict[str, Any],
        replica_instances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate overall Disaster Recovery readiness across primary and read replicas."""
        if not replica_instances:
            return {
                "dr_ready": False,
                "reason": "No cross-region or local read replicas configured for DR",
                "healthy_replicas": 0,
            }

        healthy_replicas = 0
        for r in replica_instances:
            lag = r.get("replication_lag_bytes", 0)
            status = r.get("replication_status")
            if status == "STREAMING" and lag <= 10485760:
                healthy_replicas += 1

        dr_ready = (primary_instance.get("status") == "AVAILABLE") and (healthy_replicas > 0)

        return {
            "dr_ready": dr_ready,
            "primary_status": primary_instance.get("status"),
            "total_replicas": len(replica_instances),
            "healthy_replicas": healthy_replicas,
            "rto_target_seconds": self.target_rto_seconds,
        }
