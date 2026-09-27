"""Bounded acquisition worker with claim, dispatch, reconciliation, and recovery loops."""
from __future__ import annotations
import logging
import json
import time
from datetime import datetime, timezone
from psycopg.types.json import Jsonb
from .canonical import digest_json
from .config import get_settings
from .errors import ForensicError, LabUnavailable, StaleAttempt
from .events import EventInboxService
from .service import ServiceContainer

LOG = logging.getLogger("forensics.worker")


class CollectionWorker:
    def __init__(self, services: ServiceContainer, worker_id: str | None = None):
        self.services = services
        self.worker_id = worker_id or get_settings().worker_id
        self.stopping = False
        self.processed = 0
        self.failed = 0

    def run_once(self, limit: int | None = None) -> dict[str, int]:
        recovered = self.services.queue.recover_expired_claims()
        claimed = self.services.queue.claim(self.worker_id, limit=limit)
        dispatched = 0
        errors = 0
        for item in claimed:
            try:
                plan = self.services.database.one(
                    "SELECT tenant_id,case_id,plan_digest FROM collection_plans WHERE plan_id=%s",
                    (item["plan_id"],),
                )
                if plan is None:
                    raise ForensicError("collection plan disappeared after queue claim")
                item_row = dict(item)
                result = self.services.dispatcher.dispatch(
                    item_row,
                    attempt=int(item_row["attempt"]),
                    intent_digest=str(plan["plan_digest"]),
                    tenant_id=str(plan["tenant_id"]),
                    case_id=str(item_row["case_id"]),
                )
                self.services.queue.mark_dispatched(item["item_id"], int(item["attempt"]), item["claim_token"], result)
                self._ingest_lab_result(item, plan, result)
                dispatched += 1
            except LabUnavailable as exc:
                errors += 1
                LOG.warning("ambiguous lab dispatch item=%s attempt=%s: %s", item["item_id"], item["attempt"], exc)
                try:
                    known = self.services.dispatcher.find_attempt(item["item_id"], int(item["attempt"]))
                    if known:
                        self.services.queue.mark_dispatched(item["item_id"], int(item["attempt"]), item["claim_token"], known)
                        plan = self.services.database.one(
                            "SELECT tenant_id,case_id,plan_digest FROM collection_plans WHERE plan_id=%s",
                            (item["plan_id"],),
                        )
                        if plan:
                            self._ingest_lab_result(item, plan, known)
                    else:
                        self.services.queue.schedule_retry(item["item_id"], int(item["attempt"]), str(exc))
                except ForensicError:
                    LOG.exception("ambiguous dispatch reconciliation failed item=%s", item["item_id"])
            except StaleAttempt:
                errors += 1
                LOG.info("stale worker action fenced item=%s attempt=%s", item["item_id"], item["attempt"])
            except Exception:
                errors += 1
                self.failed += 1
                LOG.exception("worker action failed item=%s attempt=%s", item["item_id"], item["attempt"])
        reconciled = self.services.reconciler.process_batch(limit or get_settings().worker_batch_size)
        self.services.database.execute(
            "INSERT INTO worker_checkpoints(worker_name,stream,position,fence_token,heartbeat_at,details) "
            "VALUES(%s,'worker',%s,%s,%s,%s) ON CONFLICT(worker_name,stream) DO UPDATE SET position=greatest(worker_checkpoints.position,EXCLUDED.position),fence_token=EXCLUDED.fence_token,heartbeat_at=EXCLUDED.heartbeat_at,details=EXCLUDED.details",
            (self.worker_id, self.processed + dispatched, f"{self.worker_id}:{self.processed}", datetime.now(timezone.utc), Jsonb({"recovered": recovered, "reconciled": reconciled})),
        )
        self.processed += dispatched
        return {"claimed": len(claimed), "dispatched": dispatched, "recovered": recovered, "reconciled": reconciled.get("applied", 0), "errors": errors}

    def _ingest_lab_result(self, item: dict, plan: dict, result: dict) -> None:
        status = str(result.get("status", "failed"))
        event_type = "collection.completed" if status in {"complete", "partial"} else "collection.failed"
        envelope = {
            "event_type": event_type,
            "delivery_id": "delivery_" + str(result.get("run_id", item["item_id"] + str(item["attempt"]))),
            "tenant_id": plan["tenant_id"],
            "case_id": plan["case_id"],
            "endpoint_id": item["endpoint_id"],
            "source_id": item["source_id"],
            "plan_id": item["plan_id"],
            "collection_item_id": item["item_id"],
            "attempt": int(item["attempt"]),
            "status": status,
            "occurred_at": result.get("observed_at") or datetime.now(timezone.utc).isoformat(),
            "payload_digest": digest_json(result),
            "evidence": result.get("artifacts", []),
            "run_id": result.get("run_id"),
        }
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = EventInboxService.sign(self.services.events.secret.decode(), raw)
        self.services.events.ingest(raw, signature, event_type)

    def run_forever(self, idle_seconds: float = 1.0) -> None:
        self.services.bootstrap()
        while not self.stopping:
            result = self.run_once()
            if result["claimed"] == 0 and result["reconciled"] == 0:
                time.sleep(max(0.05, min(idle_seconds, 10.0)))


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    worker = CollectionWorker(ServiceContainer.build())
    worker.run_forever()


if __name__ == "__main__":
    from .service import ServiceContainer
    main()
