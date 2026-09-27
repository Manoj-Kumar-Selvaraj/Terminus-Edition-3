"""Durable queue claims, attempt allocation, and worker leases."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
from psycopg.types.json import Jsonb
from .config import get_settings
from .database import Database
from .errors import NotFound, StaleAttempt
from .canonical import stable_key


class QueueService:
    def __init__(self, database: Database):
        self.db = database
        self.settings = get_settings()

    def claim(self, worker_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        worker = worker_id.strip()
        if not worker:
            raise ValueError("worker_id is required")
        count = max(1, min(limit or self.settings.worker_batch_size, 200))
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=self.settings.worker_lease_seconds)
        token = secrets.token_hex(24)
        claimed: list[dict[str, Any]] = []
        with self.db.transaction("READ COMMITTED") as conn:
            rows = conn.execute(
                "SELECT q.queue_id,q.item_id,q.attempt,i.plan_id,i.case_id,i.endpoint_id,i.source_id,i.mode,i.artifact_families,i.byte_limit,i.deadline "
                "FROM dispatch_queue q JOIN collection_items i USING(item_id) "
                "WHERE q.state IN ('ready','retry') AND q.available_at<=%s "
                "ORDER BY q.queue_id LIMIT %s FOR UPDATE OF q SKIP LOCKED",
                (now, count),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE dispatch_queue SET state='claimed',worker_id=%s,claim_token=%s,claim_deadline=%s,delivery_attempts=delivery_attempts+1,updated_at=%s WHERE queue_id=%s",
                    (worker, token, deadline, now, row["queue_id"]),
                )
                conn.execute(
                    "INSERT INTO worker_leases(lease_id,item_id,attempt,worker_id,token,deadline,acquired_at) VALUES(%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT(item_id,attempt) DO UPDATE SET worker_id=EXCLUDED.worker_id,token=EXCLUDED.token,deadline=EXCLUDED.deadline,released_at=NULL",
                    ("lease_" + stable_key("lease", row["item_id"], str(row["attempt"]))[:24], row["item_id"], row["attempt"], worker, token, deadline, now),
                )
                conn.execute(
                    "UPDATE collection_items SET disposition='running',active_attempt=%s,updated_at=%s WHERE item_id=%s",
                    (row["attempt"], now, row["item_id"]),
                )
                conn.execute(
                    "INSERT INTO collection_attempts(item_id,attempt,worker_id,attempt_token,state,created_at,updated_at) VALUES(%s,%s,%s,%s,'claimed',%s,%s) ON CONFLICT(item_id,attempt) DO NOTHING",
                    (row["item_id"], row["attempt"], worker, token, now, now),
                )
                claimed.append({**row, "worker_id": worker, "claim_token": token, "claim_deadline": deadline})
        return claimed

    def renew(self, item_id: str, attempt: int, token: str, worker_id: str) -> datetime:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(seconds=self.settings.worker_lease_timeout_sec if hasattr(self.settings, "worker_lease_timeout_sec") else self.settings.worker_lease_seconds)
        with self.db.transaction() as conn:
            result = conn.execute(
                "UPDATE worker_leases SET deadline=%s WHERE item_id=%s AND attempt=%s AND token=%s AND worker_id=%s AND released_at IS NULL AND deadline>%s RETURNING lease_id",
                (deadline, item_id, attempt, token, worker_id, now),
            ).fetchone()
            if result is None:
                raise StaleAttempt("lease is expired or fenced")
        return deadline

    def mark_dispatched(self, item_id: str, attempt: int, token: str, acknowledgement: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            row = conn.execute(
                "SELECT q.queue_id,q.worker_id,q.claim_token,i.active_attempt FROM dispatch_queue q JOIN collection_items i USING(item_id) "
                "WHERE q.item_id=%s AND q.attempt=%s FOR UPDATE OF q,i",
                (item_id, attempt),
            ).fetchone()
            if row is None or row["claim_token"] != token or row["active_attempt"] != attempt:
                raise StaleAttempt("dispatch acknowledgement belongs to a stale attempt")
            conn.execute(
                "UPDATE dispatch_queue SET state='dispatched',acknowledgement=%s,updated_at=%s WHERE queue_id=%s",
                (Jsonb(acknowledgement), now, row["queue_id"]),
            )
            conn.execute(
                "UPDATE collection_attempts SET state='dispatched',dispatched_at=%s,updated_at=%s WHERE item_id=%s AND attempt=%s",
                (now, now, item_id, attempt),
            )

    def schedule_retry(self, item_id: str, attempt: int, reason: str, *, delay_seconds: int = 5) -> int:
        now = datetime.now(timezone.utc)
        new_attempt = attempt + 1
        with self.db.transaction("SERIALIZABLE") as conn:
            current = conn.execute("SELECT active_attempt FROM collection_items WHERE item_id=%s FOR UPDATE", (item_id,)).fetchone()
            if current is None:
                raise NotFound("collection item not found")
            if int(current["active_attempt"]) != attempt:
                raise StaleAttempt("attempt changed before retry scheduling")
            conn.execute("UPDATE collection_attempts SET state='failed',updated_at=%s WHERE item_id=%s AND attempt=%s", (now, item_id, attempt))
            conn.execute("UPDATE worker_leases SET released_at=%s WHERE item_id=%s AND attempt=%s AND released_at IS NULL", (now, item_id, attempt))
            conn.execute("UPDATE collection_items SET disposition='queued',active_attempt=%s,updated_at=%s WHERE item_id=%s", (new_attempt, now, item_id))
            conn.execute(
                "INSERT INTO collection_attempts(item_id,attempt,worker_id,attempt_token,state,result_payload,created_at,updated_at) VALUES(%s,%s,'scheduler',%s,'queued',%s,%s,%s)",
                (item_id, new_attempt, secrets.token_hex(24), Jsonb({"retry_reason": reason[:256]}), now, now),
            )
            conn.execute(
                "INSERT INTO dispatch_queue(item_id,attempt,state,available_at,created_at,updated_at) VALUES(%s,%s,'retry',%s,%s,%s)",
                (item_id, new_attempt, now + timedelta(seconds=max(1, min(delay_seconds, 3600))), now, now),
            )
        return new_attempt

    def recover_expired_claims(self) -> int:
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            rows = conn.execute(
                "UPDATE dispatch_queue SET state='retry',worker_id=NULL,claim_token=NULL,claim_deadline=NULL,available_at=%s,updated_at=%s "
                "WHERE state='claimed' AND claim_deadline<=%s RETURNING item_id,attempt",
                (now, now, now),
            ).fetchall()
            for row in rows:
                conn.execute("UPDATE worker_leases SET released_at=%s WHERE item_id=%s AND attempt=%s AND released_at IS NULL", (now, row["item_id"], row["attempt"]))
                conn.execute("UPDATE collection_attempts SET state='expired',updated_at=%s WHERE item_id=%s AND attempt=%s", (now, row["item_id"], row["attempt"]))
            return len(rows)
