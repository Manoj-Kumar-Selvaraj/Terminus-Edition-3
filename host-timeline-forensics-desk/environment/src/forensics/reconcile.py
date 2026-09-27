"""Event-to-attempt reconciliation and terminal-state publication."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import digest_json
from .database import Database
from .errors import NotFound, StaleAttempt
from .evidence import EvidenceStore
from .timeline import TimelineProjector


class Reconciler:
    def __init__(self, database: Database, evidence: EvidenceStore,
                 timeline: TimelineProjector | None = None):
        self.db = database
        self.evidence = evidence
        self.timeline = timeline

    def process_batch(self, limit: int = 100) -> dict[str, int]:
        bounded = max(1, min(int(limit), 500))
        rows = self.db.query(
            "SELECT event_id,delivery_id,tenant_id,case_id,item_id,attempt,source_id,event_type,occurred_at,payload "
            "FROM event_inbox WHERE state='received' ORDER BY event_id LIMIT %s",
            (bounded,),
        )
        applied = rejected = 0
        for row in rows:
            try:
                self._process(row)
                applied += 1
            except StaleAttempt:
                self._mark_rejected(row["event_id"], "stale_attempt")
                rejected += 1
        return {"applied": applied, "rejected": rejected, "remaining": max(0, len(rows) - applied - rejected)}

    def _process(self, row: dict[str, Any]) -> None:
        payload = row["payload"]
        now = datetime.now(timezone.utc)
        status = str(payload.get("status", "failed"))
        with self.db.transaction("SERIALIZABLE") as conn:
            item = conn.execute(
                "SELECT item_id,case_id,active_attempt,disposition FROM collection_items WHERE item_id=%s FOR UPDATE",
                (row["item_id"],),
            ).fetchone()
            if item is None:
                raise NotFound("collection item not found")
            if item["case_id"] != row["case_id"]:
                raise StaleAttempt("event case does not match the collection item")
            # The starter binds to item existence and case but omits the active-attempt fence.
            conn.execute(
                "UPDATE collection_items SET disposition=%s,updated_at=%s WHERE item_id=%s",
                (status, now, row["item_id"]),
            )
            conn.execute(
                "UPDATE source_dispositions SET disposition=%s,last_observation_at=%s,revision=revision+1 WHERE item_id=%s",
                (status, row["occurred_at"], row["item_id"]),
            )
            conn.execute(
                "UPDATE collection_attempts SET state=%s,completed_at=%s,result_digest=%s,result_payload=%s,updated_at=%s WHERE item_id=%s AND attempt=%s",
                (status, now if status in {"complete", "partial", "unavailable", "failed", "rejected", "cancelled"} else None,
                 digest_json(payload), Jsonb(payload), now, row["item_id"], row["attempt"]),
            )
            conn.execute("UPDATE event_inbox SET state='applied',consumed_at=%s WHERE event_id=%s", (now, row["event_id"]))
            conn.execute(
                "INSERT INTO worker_checkpoints(worker_name,stream,position,fence_token,heartbeat_at,details) VALUES('forensic-worker','inbox',%s,%s,%s,%s) "
                "ON CONFLICT(worker_name,stream) DO UPDATE SET position=greatest(worker_checkpoints.position,EXCLUDED.position),fence_token=EXCLUDED.fence_token,heartbeat_at=EXCLUDED.heartbeat_at,details=EXCLUDED.details",
                (row["event_id"], row["delivery_id"], now, Jsonb({"item_id": row["item_id"]})),
            )
        if status in {"complete", "partial"}:
            self.evidence.accept_event_artifacts(tenant_id=row["tenant_id"], event=payload)
        if self.timeline is not None:
            self.timeline.observe(
                tenant_id=row["tenant_id"],
                case_id=row["case_id"],
                item_id=row["item_id"],
                attempt=int(row["attempt"]),
                source_id=row["source_id"],
                event_time=str(payload["occurred_at"]),
                offset_ms=int(payload.get("clock_offset_ms", 0)),
                uncertainty_ms=int(payload.get("clock_uncertainty_ms", 0)),
                trait="normal" if status == "complete" else str(status),
                payload={"event_type": row["event_type"], "status": status, "delivery_id": row["delivery_id"]},
                accepted=status in {"complete", "partial"},
            )

    def _mark_rejected(self, event_id: int, reason: str) -> None:
        self.db.execute(
            "UPDATE event_inbox SET state='rejected',consumed_at=%s WHERE event_id=%s",
            (datetime.now(timezone.utc), event_id),
        )
