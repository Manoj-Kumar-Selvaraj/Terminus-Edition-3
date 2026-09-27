"""Immutable tenant policy revisions and acquisition authorization."""
from __future__ import annotations
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import digest_json
from .database import Database
from .errors import NotFound, PolicyDenied
from .models import ActorContext, PlanRequest
from .authz import AuthorizationService


class PolicyService:
    def __init__(self, database: Database, authorization: AuthorizationService):
        self.db = database
        self.authz = authorization

    def get_revision(self, tenant_id: str, revision: str) -> dict[str, Any]:
        row = self.db.one(
            "SELECT document,digest,created_at FROM policy_revisions WHERE tenant_id=%s AND policy_revision=%s",
            (tenant_id, revision),
        )
        if row is None:
            raise NotFound("policy revision is not visible")
        return row

    def validate_plan(self, context: ActorContext, request: PlanRequest) -> dict[str, Any]:
        self.authz.require(context, "case:collect", request.case_id)
        policy = self.get_revision(context.tenant_id, request.policy_revision)
        document = policy["document"]
        allowed_modes = set(document.get("allowed_modes", []))
        allowed_sources = set(document.get("allowed_sources", []))
        maximum_bytes = int(document.get("max_case_bytes", 0))
        requested_bytes = sum(source.byte_limit for source in request.sources)
        if requested_bytes > maximum_bytes:
            raise PolicyDenied("requested collection exceeds case policy byte budget")
        rejected: list[dict[str, str]] = []
        for source in request.sources:
            if source.mode.value not in allowed_modes:
                rejected.append({"source_id": source.source_id, "reason": "mode_not_allowed"})
            if source.source_id not in allowed_sources:
                rejected.append({"source_id": source.source_id, "reason": "source_not_allowed"})
        if rejected:
            raise PolicyDenied("one or more requested sources are outside policy", details={"sources": rejected})
        return {"policy": document, "policy_digest": policy["digest"], "requested_bytes": requested_bytes}

    def source_options(self, tenant_id: str, revision: str) -> dict[str, Any]:
        document = self.get_revision(tenant_id, revision)["document"]
        return {
            "allowed_modes": list(document.get("allowed_modes", [])),
            "allowed_sources": list(document.get("allowed_sources", [])),
            "max_case_bytes": int(document.get("max_case_bytes", 0)),
        }

    def create_revision(self, tenant_id: str, revision: str, document: dict[str, Any]) -> str:
        digest = digest_json(document)
        with self.db.transaction("SERIALIZABLE") as conn:
            conn.execute(
                "INSERT INTO policy_revisions(tenant_id,policy_revision,document,digest,created_at) "
                "VALUES(%s,%s,%s,%s,clock_timestamp())",
                (tenant_id, revision, Jsonb(document), digest),
            )
        return digest
