"""Bounded audit append and case-scoped audit retrieval."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import digest_json
from .database import Database
from .models import ActorContext
from .authz import AuthorizationService


class AuditService:
    def __init__(self, database: Database, authorization: AuthorizationService):
        self.db = database
        self.authz = authorization

    def append(self, *, context: ActorContext, case_id: str | None, action: str,
               decision: str, detail: dict[str, Any], occurred_at: datetime | None = None) -> int:
        timestamp = occurred_at or datetime.now(timezone.utc)
        clean = {str(key): value for key, value in detail.items() if not self._secret_key(str(key))}
        with self.db.transaction() as conn:
            row = conn.execute(
                "INSERT INTO audit_events(tenant_id,case_id,actor_id,action,decision,detail,detail_digest,occurred_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING audit_sequence",
                (context.tenant_id, case_id, context.actor_id, action, decision, Jsonb(clean),
                 digest_json(clean), timestamp),
            ).fetchone()
            return int(row["audit_sequence"])

    def list_case(self, context: ActorContext, case_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        self.authz.require(context, "case:inspect", case_id)
        bounded = max(1, min(int(limit), 1000))
        return self.db.query(
            "SELECT audit_sequence, action, decision, detail, detail_digest, occurred_at "
            "FROM audit_events WHERE tenant_id=%s AND case_id=%s "
            "ORDER BY audit_sequence DESC LIMIT %s",
            (context.tenant_id, case_id, bounded),
        )

    @staticmethod
    def _secret_key(key: str) -> bool:
        lowered = key.lower()
        return any(part in lowered for part in ("password", "secret", "token", "credential", "private_key"))
