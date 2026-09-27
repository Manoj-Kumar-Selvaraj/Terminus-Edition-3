"""Operational readiness combines data recovery and service-worker state."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .database import Database


class ReadinessService:
    def __init__(self, database: Database, *, worker_freshness_seconds: int = 90):
        self.db = database
        self.worker_freshness_seconds = worker_freshness_seconds

    def snapshot(self) -> dict[str, Any]:
        migration = self.db.one("SELECT max(version) AS version FROM schema_migrations") or {}
        queue = self.db.one(
            "SELECT count(*) FILTER (WHERE state IN ('ready','retry')) AS ready, "
            "count(*) FILTER (WHERE state='claimed') AS claimed FROM dispatch_queue"
        ) or {}
        inbox = self.db.one(
            "SELECT count(*) AS pending FROM event_inbox WHERE state <> 'applied'"
        ) or {}
        workers = self.db.query(
            "SELECT worker_name, heartbeat_at FROM worker_checkpoints ORDER BY worker_name"
        )
        now = datetime.now(timezone.utc)
        stale = [row["worker_name"] for row in workers
                 if (now - row["heartbeat_at"]).total_seconds() > self.worker_freshness_seconds]
        pending = int(inbox.get("pending") or 0)
        ready = int(queue.get("ready") or 0)
        claimed = int(queue.get("claimed") or 0)
        healthy = not stale and pending == 0
        return {
            "status": "READY" if healthy else "DEGRADED",
            "schema_version": int(migration.get("version") or 0),
            "queue_ready": ready,
            "queue_claimed": claimed,
            "inbox_pending": pending,
            "stale_workers": stale,
            "observed_at": now.isoformat(),
        }
