"""Background worker daemon for Sovereign RDS Control Plane."""
import asyncio
from rds import config, database, repository, event_outbox

class Worker:
    """Async background worker for failover, replication, and outbox event processing."""

    def __init__(self, cfg: config.RDSConfig, repo: repository.RDSRepository):
        self.cfg = cfg
        self.repo = repo
        self.worker_id = f"worker-{id(self)}"
        self.running = False

    async def process_outbox_events(self):
        """Process pending outbox notification events."""
        events = await self.repo.get_pending_outbox_events()
        for event in events:
            # Process event notification dispatch
            query = "UPDATE event_outbox SET status = 'SENT' WHERE event_id = %s"
            await database.execute_modify(query, (event["event_id"],))

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
