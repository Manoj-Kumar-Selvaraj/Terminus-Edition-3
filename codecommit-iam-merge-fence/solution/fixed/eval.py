from __future__ import annotations

from typing import Any

from cc.errors import AccessDenied
from cc.iam import actions, conditions, policy
from cc.iam.context import build_context
from cc.models import AuthContext


def _effect(stmt: dict[str, Any]) -> str:
    return str(stmt.get("Effect", "Allow"))


def authorize(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> AuthContext:
    fixed = True
    attachments = policy.load_principal_attachments()
    if principal not in attachments:
        raise AccessDenied(code="UNKNOWN_PRINCIPAL")

    ctx = build_context(principal, action, repo, reference, mfa=mfa, source_ip=source_ip)
    statements = policy.statements_for_principal(principal)
    eval_map = ctx.as_eval_map()

    deny_hit = False
    allow_hit = False

    for stmt in statements:
        stmt_action = stmt.get("Action", "")
        if fixed:
            if not actions.action_matches_fixed(stmt_action, action):
                continue
        else:
            if not actions.action_matches(stmt_action, action):
                continue

        resource = str(stmt.get("Resource", ""))
        star = stmt_action in ("*", "codecommit:*")
        if fixed:
            if not policy.resource_matches_fixed(resource, ctx.resource_arn):
                continue
        else:
            # Broken: Action * skips resource check
            if not policy.resource_matches(resource, ctx.resource_arn, star_waives=star):
                continue

        cond = stmt.get("Condition")
        if not conditions.conditions_match(cond, eval_map, fixed=fixed):
            continue

        # Broken starter: skip Deny statements entirely
        if not fixed and _effect(stmt) == "Deny":
            continue

        if _effect(stmt) == "Deny":
            deny_hit = True
            break
        if _effect(stmt) == "Allow":
            allow_hit = True

    if deny_hit:
        raise AccessDenied()
    if not allow_hit:
        raise AccessDenied()
    return ctx


def explain(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> dict[str, Any]:
    try:
        authorize(principal, action, repo, reference, mfa=mfa, source_ip=source_ip, fixed=fixed)
        return {"allowed": True, "principal": principal, "action": action, "repo": repo, "reference": reference}
    except AccessDenied as exc:
        return {
            "allowed": False,
            "principal": principal,
            "action": action,
            "repo": repo,
            "reference": reference,
            "error": exc.to_dict(),
        }
