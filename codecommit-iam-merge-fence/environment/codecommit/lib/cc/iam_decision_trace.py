"""Authorization decision traces for operator explain / audit enrichment."""

from __future__ import annotations

from typing import Any

from cc.iam import actions, conditions, policy
from cc.iam.context import build_context


def _effect(stmt: dict[str, Any]) -> str:
    return str(stmt.get("Effect", "Allow"))


def trace_authorize(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> dict[str, Any]:
    attachments = policy.load_principal_attachments()
    if principal not in attachments:
        return {
            "allowed": False,
            "code": "UNKNOWN_PRINCIPAL",
            "steps": [],
            "principal": principal,
            "action": action,
        }

    ctx = build_context(principal, action, repo, reference, mfa=mfa, source_ip=source_ip)
    eval_map = ctx.as_eval_map()
    steps: list[dict[str, Any]] = []
    deny_hit = False
    allow_hit = False

    for idx, stmt in enumerate(policy.statements_for_principal(principal)):
        stmt_action = stmt.get("Action", "")
        action_ok = (
            actions.action_matches_fixed(stmt_action, action)
            if fixed
            else actions.action_matches(stmt_action, action)
        )
        resource = str(stmt.get("Resource", ""))
        star = stmt_action in ("*", "codecommit:*")
        if fixed:
            resource_ok = policy.resource_matches_fixed(resource, ctx.resource_arn)
        else:
            resource_ok = policy.resource_matches(resource, ctx.resource_arn, star_waives=star)
        cond_ok = conditions.conditions_match(stmt.get("Condition"), eval_map, fixed=fixed)
        matched = bool(action_ok and resource_ok and cond_ok)
        effect = _effect(stmt)
        note = None
        if matched and not fixed and effect == "Deny":
            note = "deny_skipped"
            matched = False
        step = {
            "index": idx,
            "sid": stmt.get("Sid"),
            "effect": effect,
            "action_ok": action_ok,
            "resource_ok": resource_ok,
            "condition_ok": cond_ok,
            "matched": matched,
            "note": note,
        }
        steps.append(step)
        if not matched:
            continue
        if effect == "Deny":
            deny_hit = True
            break
        if effect == "Allow":
            allow_hit = True

    allowed = bool(allow_hit and not deny_hit)
    return {
        "allowed": allowed,
        "principal": principal,
        "action": action,
        "repo": repo,
        "reference": ctx.reference,
        "resource_arn": ctx.resource_arn,
        "deny_hit": deny_hit,
        "allow_hit": allow_hit,
        "steps": steps,
        "context": eval_map,
    }


def compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "allowed": trace.get("allowed"),
        "matched_sids": [s.get("sid") for s in (trace.get("steps") or []) if s.get("matched")],
        "deny_hit": trace.get("deny_hit"),
        "step_count": len(trace.get("steps") or []),
    }
