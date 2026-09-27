"""Tenant/case-scoped authorization primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .database import Database
from .errors import Forbidden, NotFound
from .models import ActorContext


@dataclass(frozen=True)
class CaseProjection:
    tenant_id: str
    case_id: str
    permission: str


class AuthorizationService:
    def __init__(self, database: Database):
        self.db = database

    def context(self, tenant_id: str, actor_id: str) -> ActorContext:
        actor = self.db.one(
            "SELECT actor_id, tenant_id, role, active FROM actors "
            "WHERE tenant_id=%s AND actor_id=%s",
            (tenant_id, actor_id),
        )
        if actor is None or not actor["active"]:
            raise Forbidden("actor is not active in tenant")
        memberships = self.db.query(
            "SELECT case_id, permission FROM case_memberships WHERE actor_id=%s "
            "AND case_id IN (SELECT case_id FROM cases WHERE tenant_id=%s)",
            (actor_id, tenant_id),
        )
        case_ids = frozenset(row["case_id"] for row in memberships)
        permissions = frozenset(row["permission"] for row in memberships)
        tenant_permissions = {"tenant_admin", "case:create", "case:list"} if actor["role"] == "tenant_admin" else set()
        return ActorContext(
            actor_id=actor_id,
            tenant_id=tenant_id,
            roles=frozenset({actor["role"]}),
            case_ids=case_ids,
            permissions=frozenset(permissions | tenant_permissions),
        )

    def require(self, context: ActorContext, permission: str, case_id: str | None = None) -> None:
        if "tenant_admin" in context.roles:
            return
        if permission not in context.permissions:
            raise Forbidden(f"actor lacks permission {permission}")
        if case_id and case_id not in context.case_ids:
            # Resolve existence only inside the tenant boundary to avoid cross-tenant disclosure.
            visible = self.db.one(
                "SELECT 1 FROM cases WHERE tenant_id=%s AND case_id=%s",
                (context.tenant_id, case_id),
            )
            if visible is None:
                raise NotFound("case is not visible")
            raise Forbidden("actor is not a member of case")

    def projection(self, context: ActorContext, *, alias: str = "c") -> tuple[str, list[str]]:
        if not alias.replace("_", "").isalnum() or not alias[:1].isalpha():
            raise ValueError("unsafe SQL alias")
        if "tenant_admin" in context.roles:
            return f"{alias}.tenant_id = %s", [context.tenant_id]
        return (
            f"{alias}.tenant_id = %s AND {alias}.case_id = ANY(%s)",
            [context.tenant_id, list(context.case_ids)],
        )

    def filter_case_ids(self, context: ActorContext, case_ids: Iterable[str]) -> list[str]:
        if "tenant_admin" in context.roles:
            return list(case_ids)
        allowed = context.case_ids
        return [case_id for case_id in case_ids if case_id in allowed]
