"""Case lifecycle, membership, and preservation-hold operations."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from psycopg.types.json import Jsonb
from .authz import AuthorizationService
from .canonical import digest_json, normalize_case_id
from .database import Database
from .errors import Conflict, InvalidRequest, NotFound
from .models import ActorContext, CaseState


class CaseService:
    def __init__(self, database: Database, authorization: AuthorizationService):
        self.db = database
        self.authz = authorization

    def create(self, context: ActorContext, case_id: str, title: str) -> dict[str, Any]:
        self.authz.require(context, "case:create")
        normalized = normalize_case_id(case_id)
        text = title.strip()
        if not text or len(text) > 240:
            raise InvalidRequest("case title must contain 1-240 characters")
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            conn.execute(
                "INSERT INTO cases(case_id,tenant_id,title,state,revision,opened_at,updated_at,created_by) "
                "VALUES(%s,%s,%s,'open',1,%s,%s,%s)",
                (normalized, context.tenant_id, text, now, now, context.actor_id),
            )
            for permission in ("case:inspect", "case:collect", "case:export", "case:hold"):
                conn.execute(
                    "INSERT INTO case_memberships(case_id,actor_id,permission,granted_at) VALUES(%s,%s,%s,%s)",
                    (normalized, context.actor_id, permission, now),
                )
            self._audit(conn, context, normalized, "case.created", {"title": text}, now)
        return self.get(context, normalized)

    def get(self, context: ActorContext, case_id: str) -> dict[str, Any]:
        normalized = normalize_case_id(case_id)
        self.authz.require(context, "case:inspect", normalized)
        row = self.db.one(
            "SELECT case_id,tenant_id,title,state,revision,opened_at,updated_at,closed_at "
            "FROM cases WHERE tenant_id=%s AND case_id=%s",
            (context.tenant_id, normalized),
        )
        if row is None:
            raise NotFound("case is not visible")
        holds = self.db.query(
            "SELECT hold_id,reason,created_by,created_at FROM case_holds "
            "WHERE tenant_id=%s AND case_id=%s AND state='active' ORDER BY created_at,hold_id",
            (context.tenant_id, normalized),
        )
        row["holds"] = holds
        return row

    def list_cases(self, context: ActorContext, *, limit: int = 100, cursor: str | None = None) -> dict[str, Any]:
        self.authz.require(context, "case:list")
        bounded = max(1, min(int(limit), 200))
        if "tenant_admin" in context.roles:
            rows = self.db.query(
                "SELECT case_id,title,state,revision,opened_at,updated_at FROM cases "
                "WHERE tenant_id=%s ORDER BY opened_at,case_id LIMIT %s",
                (context.tenant_id, bounded + 1),
            )
        else:
            rows = self.db.query(
                "SELECT case_id,title,state,revision,opened_at,updated_at FROM cases "
                "WHERE tenant_id=%s AND case_id=ANY(%s) ORDER BY opened_at,case_id LIMIT %s",
                (context.tenant_id, list(context.case_ids), bounded + 1),
            )
        return {"rows": rows[:bounded], "has_more": len(rows) > bounded, "count": min(len(rows), bounded)}

    def set_state(self, context: ActorContext, case_id: str, state: CaseState, reason: str) -> dict[str, Any]:
        normalized = normalize_case_id(case_id)
        self.authz.require(context, "case:hold", normalized)
        if state not in {CaseState.OPEN, CaseState.HOLD, CaseState.CLOSED}:
            raise InvalidRequest("unsupported case state")
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            current = conn.execute(
                "SELECT state,revision FROM cases WHERE tenant_id=%s AND case_id=%s FOR UPDATE",
                (context.tenant_id, normalized),
            ).fetchone()
            if current is None:
                raise NotFound("case is not visible")
            if current["state"] == "closed" and state != CaseState.CLOSED:
                raise Conflict("closed case requires an explicit reopening workflow")
            conn.execute(
                "UPDATE cases SET state=%s,revision=revision+1,updated_at=%s WHERE tenant_id=%s AND case_id=%s",
                (state.value, now, context.tenant_id, normalized),
            )
            self._audit(conn, context, normalized, "case.state_changed", {"from": current["state"], "to": state.value, "reason": reason[:512]}, now)
        return self.get(context, normalized)

    def place_hold(self, context: ActorContext, case_id: str, reason: str) -> str:
        normalized = normalize_case_id(case_id)
        self.authz.require(context, "case:hold", normalized)
        if not reason.strip():
            raise InvalidRequest("hold reason is required")
        now = datetime.now(timezone.utc)
        hold_id = f"hold_{digest_json([context.tenant_id, normalized, context.actor_id, now.isoformat(), reason])[:24]}"
        with self.db.transaction("SERIALIZABLE") as conn:
            case = conn.execute(
                "SELECT state FROM cases WHERE tenant_id=%s AND case_id=%s FOR UPDATE",
                (context.tenant_id, normalized),
            ).fetchone()
            if case is None:
                raise NotFound("case is not visible")
            conn.execute(
                "INSERT INTO case_holds(hold_id,tenant_id,case_id,reason,state,created_by,created_at) "
                "VALUES(%s,%s,%s,%s,'active',%s,%s)",
                (hold_id, context.tenant_id, normalized, reason.strip()[:512], context.actor_id, now),
            )
            conn.execute(
                "UPDATE cases SET state='hold',revision=revision+1,updated_at=%s WHERE case_id=%s AND tenant_id=%s",
                (now, normalized, context.tenant_id),
            )
            self._audit(conn, context, normalized, "case.hold_placed", {"hold_id": hold_id, "reason": reason[:512]}, now)
        return hold_id

    def release_hold(self, context: ActorContext, case_id: str, hold_id: str, reason: str) -> bool:
        normalized = normalize_case_id(case_id)
        self.authz.require(context, "case:hold", normalized)
        now = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            hold = conn.execute(
                "SELECT hold_id FROM case_holds WHERE tenant_id=%s AND case_id=%s AND hold_id=%s AND state='active' FOR UPDATE",
                (context.tenant_id, normalized, hold_id),
            ).fetchone()
            if hold is None:
                return False
            conn.execute(
                "UPDATE case_holds SET state='released',released_by=%s,released_at=%s WHERE hold_id=%s",
                (context.actor_id, now, hold_id),
            )
            remaining = conn.execute(
                "SELECT count(*) AS n FROM case_holds WHERE tenant_id=%s AND case_id=%s AND state='active'",
                (context.tenant_id, normalized),
            ).fetchone()["n"]
            if remaining == 0:
                conn.execute(
                    "UPDATE cases SET state='open',revision=revision+1,updated_at=%s WHERE tenant_id=%s AND case_id=%s AND state='hold'",
                    (now, context.tenant_id, normalized),
                )
            self._audit(conn, context, normalized, "case.hold_released", {"hold_id": hold_id, "reason": reason[:512]}, now)
            return True

    @staticmethod
    def _audit(conn, context: ActorContext, case_id: str, action: str, detail: dict, now: datetime) -> None:
        conn.execute(
            "INSERT INTO audit_events(tenant_id,case_id,actor_id,action,decision,detail,detail_digest,occurred_at) "
            "VALUES(%s,%s,%s,%s,'ACCEPTED',%s,%s,%s)",
            (context.tenant_id, case_id, context.actor_id, action, Jsonb(detail), digest_json(detail), now),
        )
