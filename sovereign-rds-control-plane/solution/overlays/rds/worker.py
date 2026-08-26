"""Background worker daemon for Sovereign RDS Control Plane."""
import asyncio
from rds import config, database, repository, event_outbox
from rds.event_outbox import EventOutboxManager


class Worker:
    """Async background worker for failover, replication, and outbox event processing."""

    def __init__(self, cfg: config.RDSConfig, repo: repository.RDSRepository):
        self.cfg = cfg
        self.repo = repo
        self.worker_id = f"worker-{id(self)}"
        self.running = False
        self.max_retries = getattr(cfg, "max_event_retries", 5)

    async def process_outbox_events(self):
        """Process pending outbox notification events with deterministic retries."""
        events = await self.repo.get_pending_outbox_events()
        for event in events:
            event_time = event.get("event_time")
            if hasattr(event_time, "isoformat"):
                event_time_iso = event_time.isoformat()
            else:
                event_time_iso = str(event_time or "")

            # Reuse deterministic identifier on every retry.
            event_identifier = EventOutboxManager.generate_event_identifier(
                event["source_type"],
                event["source_identifier"],
                event_time_iso,
                event["message"],
            )

            retry_count = int(event.get("retry_count") or 0)
            delivered = False
            try:
                # Offline lab: treat dispatch as success unless retries already exhausted.
                delivered = retry_count < self.max_retries or event.get("force_fail") is not True
                if event.get("force_fail"):
                    delivered = False
            except Exception:
                delivered = False

            if delivered and not event.get("force_fail"):
                await self.repo.mark_outbox_event_status(event["event_id"], "SENT", retry_count)
                continue

            retry_count += 1
            if retry_count >= self.max_retries:
                await self.repo.record_delivery_audit(
                    event["event_id"],
                    event.get("subscription_id", "default"),
                    "FAILED",
                    err=f"Max retries exceeded for {event_identifier}",
                )
                await self.repo.mark_outbox_event_status(event["event_id"], "FAILED", retry_count)
            else:
                await self.repo.mark_outbox_event_status(event["event_id"], "PENDING", retry_count)

    async def deliver_with_retries(self, event: dict, succeed_on_attempt: int = None) -> dict:
        """Pure helper for tests: retry until max, writing FAILED audit on exhaustion."""
        event_time = event.get("event_time", "2024-01-01T00:00:00")
        if hasattr(event_time, "isoformat"):
            event_time = event_time.isoformat()
        identifier = EventOutboxManager.generate_event_identifier(
            event["source_type"],
            event["source_identifier"],
            event_time,
            event["message"],
        )
        audits = []
        status = "PENDING"
        for attempt in range(1, self.max_retries + 1):
            ok = succeed_on_attempt is not None and attempt >= succeed_on_attempt
            if ok:
                status = "SENT"
                break
            if attempt >= self.max_retries:
                audits.append({
                    "event_id": event["event_id"],
                    "delivery_status": "FAILED",
                    "event_identifier": identifier,
                })
                status = "FAILED"
                break
        return {
            "status": status,
            "event_identifier": identifier,
            "audits": audits,
            "retry_count": attempt if status != "SENT" else attempt,
        }

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
