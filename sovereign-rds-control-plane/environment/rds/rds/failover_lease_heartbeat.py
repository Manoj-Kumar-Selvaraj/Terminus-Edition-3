"""Failover worker heartbeat loop, lease extension, and quorum fencing manager."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from rds.errors import FailoverLeaseError

class FailoverLeaseHeartbeat:
    """Manages worker heartbeat loops and failover lease extensions."""

    def __init__(self, worker_id: str, lease_ttl_sec: int = 15):
        self.worker_id = worker_id
        self.lease_ttl_sec = lease_ttl_sec
        self.last_heartbeat: Optional[datetime] = None

    def send_heartbeat(self, current_lease: Dict[str, Any]) -> Dict[str, Any]:
        """Send heartbeat to extend leader lease."""
        now = datetime.now(timezone.utc)
        owner = current_lease.get("leader_worker_id")

        if owner and owner != self.worker_id:
            expires_at = current_lease.get("expires_at")
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at and expires_at > now:
                raise FailoverLeaseError(f"Lease active under worker {owner} until {expires_at.isoformat()}")

        self.last_heartbeat = now
        new_expires_at = datetime.fromtimestamp(now.timestamp() + self.lease_ttl_sec, tz=timezone.utc)

        return {
            "instance_id": current_lease.get("instance_id"),
            "leader_worker_id": self.worker_id,
            "acquired_at": now.isoformat(),
            "expires_at": new_expires_at.isoformat(),
            "heartbeat_ok": True,
        }
