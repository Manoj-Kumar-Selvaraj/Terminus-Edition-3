"""Case coverage and timeline projections."""
from __future__ import annotations
from typing import Any
from .authz import AuthorizationService
from .database import Database
from .errors import NotFound
from .models import ActorContext


class CoverageService:
    def __init__(self, database: Database, authorization: AuthorizationService):
        self.db = database
        self.authz = authorization

    def summary(self, context: ActorContext, case_id: str) -> dict[str, Any]:
        self.authz.require(context, "case:inspect", case_id)
        case = self.db.one("SELECT case_id,state,revision FROM cases WHERE tenant_id=%s AND case_id=%s", (context.tenant_id, case_id))
        if case is None:
            raise NotFound("case is not visible")
        requested = self.db.one(
            "SELECT count(*) AS count,count(*) FILTER (WHERE required) AS required "
            "FROM collection_items WHERE case_id=%s",
            (case_id,),
        ) or {"count": 0, "required": 0}
        completed = self.db.one(
            "SELECT count(*) AS count,coalesce(sum(byte_length),0) AS bytes "
            "FROM evidence_items WHERE tenant_id=%s AND case_id=%s AND validation_state='verified'",
            (context.tenant_id, case_id),
        ) or {"count": 0, "bytes": 0}
        dispositions = self.db.query(
            "SELECT disposition,count(*)::int AS count FROM source_dispositions "
            "WHERE tenant_id=%s AND case_id=%s GROUP BY disposition ORDER BY disposition",
            (context.tenant_id, case_id),
        )
        return {
            "case_id": case_id,
            "case_state": case["state"],
            "case_revision": case["revision"],
            "requested_sources": int(requested["count"]),
            "required_sources": int(requested["required"]),
            "verified_evidence_items": int(completed["count"]),
            "verified_bytes": int(completed["bytes"]),
            "dispositions": {row["disposition"]: row["count"] for row in dispositions},
            "complete": int(completed["count"]) >= int(requested["required"]),
        }

    def timeline(self, context: ActorContext, case_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        self.authz.require(context, "case:inspect", case_id)
        bounded = max(1, min(int(limit), 2000))
        return self.db.query(
            "SELECT e.evidence_id,e.endpoint_id,e.source_id,e.item_id,e.attempt,e.digest,e.capture_time,e.traits "
            "FROM evidence_items e WHERE e.tenant_id=%s AND e.case_id=%s "
            "ORDER BY e.capture_time,e.source_id,e.evidence_id LIMIT %s",
            (context.tenant_id, case_id, bounded),
        )

    def custody(self, context: ActorContext, case_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        self.authz.require(context, "case:inspect", case_id)
        return self.db.query(
            "SELECT custody_sequence,custody_id,evidence_id,actor_id,action,reason,event_digest,occurred_at "
            "FROM custody_events WHERE tenant_id=%s AND case_id=%s ORDER BY custody_sequence LIMIT %s",
            (context.tenant_id, case_id, max(1, min(int(limit), 1000))),
        )
