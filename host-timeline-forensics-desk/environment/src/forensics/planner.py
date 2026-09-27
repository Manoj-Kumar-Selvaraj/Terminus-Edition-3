"""Case-scoped collection-plan compilation and logical idempotency."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from psycopg.types.json import Jsonb
from .authz import AuthorizationService
from .canonical import digest_json, stable_key
from .database import Database
from .errors import Conflict, NotFound, PolicyDenied
from .inventory import InventoryService
from .models import ActorContext, PlanRequest
from .policy import PolicyService
from .source_catalog import SourceCatalog
from .state_machine import PLAN_TRANSITIONS, transition


class PlanService:
    def __init__(self, database: Database, authorization: AuthorizationService,
                 inventory: InventoryService, policies: PolicyService,
                 catalog: SourceCatalog | None = None):
        self.db = database
        self.authz = authorization
        self.inventory = inventory
        self.policies = policies
        self.catalog = catalog or SourceCatalog()

    def preview(self, context: ActorContext, request: PlanRequest) -> dict[str, Any]:
        self.authz.require(context, "case:collect", request.case_id)
        case = self.db.one(
            "SELECT case_id,state,revision FROM cases WHERE tenant_id=%s AND case_id=%s",
            (context.tenant_id, request.case_id),
        )
        if case is None:
            raise NotFound("case is not visible")
        if case["state"] != "open":
            raise PolicyDenied("collection cannot be planned for a held or closed case")
        policy_result = self.policies.validate_plan(context, request)
        compatible: list[dict[str, Any]] = []
        unsupported: list[dict[str, str]] = []
        for source in request.sources:
            endpoint = self.inventory.get_endpoint(context.tenant_id, source.endpoint_id)
            available = (endpoint.get("capabilities") or {}).get("sources", [])
            catalog_ok, reasons = self.catalog.supports(
                source.source_id, str(endpoint["platform"]), source.mode, source.artifact_families
            )
            if source.source_id not in available or not catalog_ok:
                unsupported.append({"endpoint_id": source.endpoint_id, "source_id": source.source_id, "reason": ",".join(reasons) or "source_unsupported"})
                continue
            compatible.append({
                "endpoint_id": source.endpoint_id,
                "source_id": source.source_id,
                "mode": source.mode.value,
                "artifact_families": sorted(set(source.artifact_families)),
                "byte_limit": source.byte_limit,
                "deadline": source.deadline.isoformat(),
                "required": source.required,
            })
        if not compatible:
            raise PolicyDenied("collection plan contains no compatible sources", details={"unsupported": unsupported})
        intent = {
            "tenant_id": context.tenant_id,
            "case_id": request.case_id,
            "case_revision": case["revision"],
            "actor_id": context.actor_id,
            "sources": compatible,
            # The plan stores these fields; the starter digest path is narrower than the complete intent.
            "policy_revision": request.policy_revision,
            "inventory_generation": request.inventory_generation,
            "requested_bytes": policy_result["requested_bytes"],
        }
        digest_fields = {
            "tenant_id": context.tenant_id,
            "case_id": request.case_id,
            "case_revision": case["revision"],
            "actor_id": context.actor_id,
            "sources": [
                {"endpoint_id": item["endpoint_id"], "source_id": item["source_id"], "artifact_families": item["artifact_families"]}
                for item in compatible
            ],
        }
        return {
            "intent": intent,
            "plan_digest": digest_json(digest_fields),
            "compatible_sources": compatible,
            "unsupported_sources": unsupported,
            "requested_bytes": policy_result["requested_bytes"],
            "case_revision": case["revision"],
        }

    def create(self, context: ActorContext, request: PlanRequest) -> dict[str, Any]:
        preview = self.preview(context, request)
        transition("draft", "validated", PLAN_TRANSITIONS, label="collection plan")
        transition("validated", "queued", PLAN_TRANSITIONS, label="collection plan")
        now = datetime.now(timezone.utc)
        plan_digest = preview["plan_digest"]
        with self.db.transaction("SERIALIZABLE") as conn:
            prior = conn.execute(
                "SELECT k.plan_digest,k.plan_id FROM idempotency_keys k "
                "WHERE tenant_id=%s AND actor_id=%s AND idempotency_key=%s FOR UPDATE",
                (context.tenant_id, context.actor_id, request.idempotency_key),
            ).fetchone()
            if prior:
                if prior["plan_digest"] != plan_digest:
                    raise Conflict("idempotency key was reused for another collection intent")
                row = conn.execute(
                    "SELECT plan_id,case_id,policy_revision,plan_digest,state,created_at "
                    "FROM collection_plans WHERE plan_id=%s",
                    (prior["plan_id"],),
                ).fetchone()
                return self._plan_view(conn, row)

            plan_id = "plan_" + stable_key("plan", context.tenant_id, request.case_id, request.idempotency_key)[:32]
            intent = preview["intent"]
            conn.execute(
                "INSERT INTO collection_plans(plan_id,tenant_id,case_id,case_revision,policy_revision,inventory_generation,requested_by,intent,plan_digest,state,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'validated',%s)",
                (plan_id, context.tenant_id, request.case_id, intent["case_revision"], request.policy_revision,
                 request.inventory_generation, context.actor_id, Jsonb(intent), plan_digest, now),
            )
            conn.execute(
                "INSERT INTO plan_revisions(plan_id,revision,digest,document,created_at) VALUES(%s,1,%s,%s,%s)",
                (plan_id, plan_digest, Jsonb(intent), now),
            )
            conn.execute(
                "INSERT INTO idempotency_keys(tenant_id,actor_id,idempotency_key,plan_digest,plan_id,created_at) VALUES(%s,%s,%s,%s,%s,%s)",
                (context.tenant_id, context.actor_id, request.idempotency_key, plan_digest, plan_id, now),
            )
            for index, source in enumerate(preview["compatible_sources"]):
                item_id = "item_" + stable_key("item", plan_id, source["endpoint_id"], source["source_id"], str(index))[:32]
                conn.execute(
                    "INSERT INTO collection_items(item_id,plan_id,case_id,endpoint_id,source_id,mode,artifact_families,byte_limit,deadline,required,disposition,active_attempt,created_at,updated_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'requested',0,%s,%s)",
                    (item_id, plan_id, request.case_id, source["endpoint_id"], source["source_id"], source["mode"],
                     Jsonb(source["artifact_families"]), source["byte_limit"], source["deadline"], source["required"], now, now),
                )
                conn.execute(
                    "INSERT INTO source_dispositions(item_id,tenant_id,case_id,endpoint_id,source_id,disposition) VALUES(%s,%s,%s,%s,%s,'requested')",
                    (item_id, context.tenant_id, request.case_id, source["endpoint_id"], source["source_id"]),
                )
                conn.execute(
                    "INSERT INTO dispatch_queue(item_id,attempt,state,available_at,created_at,updated_at) VALUES(%s,1,'ready',%s,%s,%s)",
                    (item_id, now, now, now),
                )
            conn.execute(
                "UPDATE collection_plans SET state='queued' WHERE plan_id=%s",
                (plan_id,),
            )
        return {
            "plan_id": plan_id,
            "case_id": request.case_id,
            "policy_revision": request.policy_revision,
            "plan_digest": plan_digest,
            "state": "queued",
            "item_count": len(preview["compatible_sources"]),
            "unsupported_sources": preview["unsupported_sources"],
            "created_at": now,
        }

    @staticmethod
    def _plan_view(conn, row: dict[str, Any]) -> dict[str, Any]:
        count = conn.execute(
            "SELECT count(*) AS n FROM collection_items WHERE plan_id=%s",
            (row["plan_id"],),
        ).fetchone()["n"]
        return {
            "plan_id": row["plan_id"], "case_id": row["case_id"],
            "policy_revision": row["policy_revision"], "plan_digest": row["plan_digest"],
            "state": row["state"], "item_count": int(count), "created_at": row["created_at"],
        }
