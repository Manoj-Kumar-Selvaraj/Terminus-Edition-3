"""Audit logging, metric calculations, and SLA telemetry for Sovereign RDS Control Plane."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class AuditMetricsEngine:
    """Manages audit log recording and SLA metric calculations."""

    def __init__(self):
        self.audit_records: List[Dict[str, Any]] = []
        self.metrics_history: List[Dict[str, Any]] = []

    def record_audit_event(
        self,
        event_type: str,
        actor: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an audit trail event."""
        entry = {
            "event_type": event_type,
            "actor": actor,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.audit_records.append(entry)
        return entry

    def calculate_availability_sla(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate system-wide availability SLA metrics."""
        total = len(instances)
        if total == 0:
            return {"sla_percentage": 100.0, "total": 0, "available": 0, "degraded": 0}

        available = sum(1 for i in instances if i.get("status") == "AVAILABLE")
        degraded = sum(1 for i in instances if i.get("status") in ("MODIFYING", "REBOOTING", "FAILOVER"))
        failed = sum(1 for i in instances if i.get("status") in ("FAILED", "UNREACHABLE"))

        sla = round((available / total) * 100.0, 2)
        return {
            "sla_percentage": sla,
            "total_instances": total,
            "available_instances": available,
            "degraded_instances": degraded,
            "failed_instances": failed,
        }

    def calculate_replication_telemetry(self, replicas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate replication lag metrics across read replicas."""
        if not replicas:
            return {"avg_lag_bytes": 0, "max_lag_bytes": 0, "healthy_replicas": 0, "lagging_replicas": 0}

        lags = [r.get("replication_lag_bytes", 0) for r in replicas]
        max_lag = max(lags)
        avg_lag = sum(lags) / len(lags)
        healthy = sum(1 for r in replicas if r.get("replication_lag_bytes", 0) <= 10485760 and r.get("replication_status") == "STREAMING")
        lagging = len(replicas) - healthy

        return {
            "avg_lag_bytes": round(avg_lag, 2),
            "max_lag_bytes": max_lag,
            "healthy_replicas": healthy,
            "lagging_replicas": lagging,
            "total_replicas": len(replicas),
        }
