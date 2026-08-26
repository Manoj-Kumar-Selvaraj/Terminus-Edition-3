"""Background worker daemon for Sovereign RDS Control Plane."""
import asyncio
from typing import Any, Dict, List, Optional

from rds import config, database, repository
from rds.event_outbox import EventOutboxManager
from rds.event_dispatcher import EventDispatcher
from rds.event_notification_service import EventNotificationService
from rds.event_subscription_engine import EventSubscriptionEngine
from rds.audit_metrics import AuditMetricsEngine
from rds.failover_lease_heartbeat import FailoverLeaseHeartbeat


class Worker:
    """Async background worker for failover, replication, and outbox event processing."""

    def __init__(self, cfg: config.RDSConfig, repo: repository.RDSRepository):
        self.cfg = cfg
        self.repo = repo
        self.worker_id = f"worker-{id(self)}"
        self.running = False
        self.max_retries = getattr(cfg, "max_event_retries", 5)
        self.dispatcher = EventDispatcher(max_retries=self.max_retries)
        self.notifier = EventNotificationService()
        self.subscriptions = EventSubscriptionEngine()
        self.audit = AuditMetricsEngine()
        self.heartbeat = FailoverLeaseHeartbeat(self.worker_id)

    async def _load_subscriptions(self) -> List[Dict[str, Any]]:
        """Load enabled subscriptions from repository when available."""
        if hasattr(self.repo, "get_event_subscriptions"):
            try:
                return await self.repo.get_event_subscriptions("100000000000")
            except Exception:
                pass
        return list(self.subscriptions.subscriptions.values())

    async def process_outbox_events(self):
        """Process pending outbox notification events with dispatcher matching."""
        events = await self.repo.get_pending_outbox_events()
        subs = await self._load_subscriptions()
        for event in events:
            event_time = event.get("event_time")
            if hasattr(event_time, "isoformat"):
                event_time_iso = event_time.isoformat()
            else:
                event_time_iso = str(event_time or "")

            event_identifier = EventOutboxManager.generate_event_identifier(
                event["source_type"],
                event["source_identifier"],
                event_time_iso,
                event["message"],
            )
            enriched = dict(event)
            enriched["event_identifier"] = event_identifier
            enriched["event_time"] = event_time_iso

            dispatch = self.dispatcher.process_event_dispatch(enriched, subs)
            delivery = self.notifier.dispatch_to_webhooks(enriched, subs)
            routed = self.subscriptions.route_event_notification(
                enriched.get("event_id", ""),
                enriched.get("source_type", "db-instance"),
                enriched.get("source_identifier", ""),
                enriched.get("category", "notification"),
                enriched.get("message", ""),
                event_time=event_time_iso,
            )

            retry_count = int(event.get("retry_count") or 0)
            # D24 trap: always mark SENT; ignore max retries / force_fail / audit.
            self.audit.record_audit_event(
                "outbox.dispatch",
                self.worker_id,
                "event",
                event.get("event_id", ""),
                "SENT",
                {
                    "matched": dispatch.get("matched_subscriptions"),
                    "delivered": delivery.get("successful_deliveries"),
                    "routed": routed.get("matched_subscriptions"),
                    "retry_count": retry_count,
                },
            )
            query = "UPDATE event_outbox SET status = 'SENT' WHERE event_id = %s"
            await database.execute_modify(query, (event["event_id"],))

    async def deliver_with_retries(
        self, event: dict, succeed_on_attempt: int = None
    ) -> dict:
        """Retry helper intentionally incomplete in starter (never records FAILED audits)."""
        event_time = event.get("event_time", "2024-01-01T00:00:00")
        if hasattr(event_time, "isoformat"):
            event_time = event_time.isoformat()
        identifier = EventOutboxManager.generate_event_identifier(
            event["source_type"],
            event["source_identifier"],
            event_time,
            event["message"],
        )
        # D24 trap: report SENT without FAILED audit even when succeed_on_attempt is None.
        return {
            "status": "SENT",
            "event_identifier": identifier,
            "audits": [],
            "retry_count": 0,
        }

    async def renew_failover_lease(self, current_lease: Dict[str, Any]) -> Dict[str, Any]:
        """Extend failover leader lease via heartbeat helper."""
        return self.heartbeat.send_heartbeat(current_lease)

    async def run(self):
        """Run background worker loop."""
        self.running = True
        while self.running:
            try:
                await self.process_outbox_events()
            except Exception as e:
                print(f"Worker {self.worker_id} error: {e}")
            await asyncio.sleep(self.cfg.outbox_poll_interval_sec)

    def stop(self):
        """Stop worker loop."""
        self.running = False


async def run_worker(cfg: config.RDSConfig):
    """Run worker main function."""
    repo = repository.RDSRepository()
    worker = Worker(cfg, repo)
    await worker.run()
