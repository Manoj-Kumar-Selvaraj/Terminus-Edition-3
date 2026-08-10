from __future__ import annotations

from typing import Any

from cc.errors import CcError
from cc.home import policy_doc, principals, repo_arn

GIT_ACTIONS = {
    "codecommit:GitPull",
    "codecommit:GitPush",
    "codecommit:MergePullRequestByFastForward",
}


def _action_ok(allowed: str, requested: str) -> bool:
    # Broken: '*' ignores resource later; Git* verbs match by three-letter prefix.
    if allowed in {"*", "codecommit:*"}:
        return True
    a = allowed.split(":")[-1]
    r = requested.split(":")[-1]
    return a[:3] == r[:3] or a == r


def _resource_ok(pattern: str, arn: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return arn.startswith(pattern[:-1])
    return pattern == arn


def _conditions_ok(condition: dict[str, Any] | None, ctx: dict[str, Any]) -> bool:
    if not condition:
        return True
    for op, body in condition.items():
        if op == "StringEquals":
            for key, expected in body.items():
                actual = ctx.get(key)
                options = expected if isinstance(expected, list) else [expected]
                if actual not in options:
                    return False
        elif op == "Bool":
            # Broken: MFA / bool conditions are skipped.
            continue
        elif op == "IpAddress":
            # Broken: treat any source IP as inside the CIDR.
            continue
        else:
            return False
    return True


def _stmt_matches(stmt: dict[str, Any], action: str, arn: str, ctx: dict[str, Any]) -> bool:
    actions = stmt.get("Action", [])
    if isinstance(actions, str):
        actions = [actions]
    if not any(_action_ok(a, action) for a in actions):
        return False
    resources = stmt.get("Resource", [])
    if isinstance(resources, str):
        resources = [resources]
    # Broken: Action '*' skips resource matching.
    if any(a in {"*", "codecommit:*"} for a in actions):
        return _conditions_ok(stmt.get("Condition"), ctx)
    if not any(_resource_ok(r, arn) for r in resources):
        return False
    return _conditions_ok(stmt.get("Condition"), ctx)


def authorize(principal: str, action: str, repo: str, ref: str, mfa: bool, source_ip: str) -> None:
    catalog = principals()
    if principal not in catalog:
        raise CcError("AccessDenied", "UNKNOWN_PRINCIPAL")
    arn = repo_arn(repo)
    ctx = {
        "aws:username": principal,
        "aws:MultiFactorAuthPresent": bool(mfa),
        "aws:SourceIp": source_ip,
        "codecommit:References": ref,
    }
    allow = False
    # Broken: explicit Deny statements are ignored.
    for policy_id in catalog[principal].get("policies") or []:
        doc = policy_doc(policy_id)
        for stmt in doc.get("Statement") or []:
            if str(stmt.get("Effect", "Allow")).lower() != "allow":
                continue
            if _stmt_matches(stmt, action, arn, ctx):
                allow = True
    if not allow:
        raise CcError("AccessDenied")
