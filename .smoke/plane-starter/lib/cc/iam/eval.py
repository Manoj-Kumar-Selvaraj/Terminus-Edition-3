"""Policy evaluation and the single authorization choke point.

Every mutating operator path — CLI or HTTP — reaches :func:`authorize`, so a
decision and its recorded audit row are produced in exactly one place.
"""

from __future__ import annotations

from typing import Any

from cc.audit.log import record_decision
from cc.errors import AccessDenied
from cc.home import principal
from cc.iam import conditions, context
from cc.iam.actions import any_action_matches, wildcard_patterns
from cc.iam.policy import any_resource_matches, statements_for, target_arn
from cc.models import Decision, RequestContext, Statement

REASON_ALLOWED = "allowed_by_policy"
REASON_EXPLICIT_DENY = "explicit_deny"
REASON_NO_ALLOW = "no_matching_allow"
REASON_UNKNOWN = "unknown_principal"


def _statement_applies(
    statement: Statement, request: RequestContext, arn: str
) -> tuple[bool, str]:
    """Test one statement against the request, reporting what rejected it."""
    if not any_action_matches(statement.actions, request.action):
        return False, "action"
    if not wildcard_patterns(statement.actions):
        if not any_resource_matches(statement.resources, arn):
            return False, "resource"
    outcome = conditions.evaluate(statement.condition, request.keys())
    if not outcome.satisfied:
        return False, f"condition:{outcome.operator or 'unknown'}"
    return True, "match"


def evaluate(request: RequestContext) -> Decision:
    """Evaluate the request against every statement attached to the principal."""
    if principal(request.principal) is None:
        return Decision(False, REASON_UNKNOWN)
    arn = target_arn(request.repo)
    statements = statements_for(request.principal)
    matched_allow: Statement | None = None
    for statement in statements:
        if not statement.is_allow:
            continue
        applies, _why = _statement_applies(statement, request, arn)
        if applies and matched_allow is None:
            matched_allow = statement
    if matched_allow is not None:
        return Decision(True, REASON_ALLOWED, matched_allow.sid, matched_allow.policy_id)
    return Decision(False, REASON_NO_ALLOW)


def probe(
    name: str,
    action: str,
    repo: str,
    *,
    ref: str | None = None,
    mfa: Any = None,
    source_ip: str | None = None,
) -> Decision:
    """Evaluate a request without recording a decision row.

    Used for read-side filtering, such as listing the repositories a caller may
    see, where one operator command inspects many resources.
    """
    request = context.build(name, action, repo, ref=ref, mfa=mfa, source_ip=source_ip)
    return evaluate(request)


def authorize(
    name: str,
    action: str,
    repo: str,
    *,
    ref: str | None = None,
    mfa: Any = None,
    source_ip: str | None = None,
) -> Decision:
    """Authorize one request, record the decision, and raise when denied."""
    request = context.build(name, action, repo, ref=ref, mfa=mfa, source_ip=source_ip)
    decision = evaluate(request)
    record_decision(request, decision)
    if decision.allowed:
        return decision
    if decision.reason == REASON_UNKNOWN:
        raise AccessDenied("UNKNOWN_PRINCIPAL", f"no such principal {name!r}")
    raise AccessDenied("POLICY_DENY", f"{action} on {repo} is not permitted for {name}")
