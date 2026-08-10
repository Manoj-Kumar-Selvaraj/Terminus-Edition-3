from __future__ import annotations

import ipaddress
from typing import Any

from cc.errors import CcError
from cc.home import policy_doc, principals, repo_arn

GIT_ACTIONS = {
    "codecommit:GitPull",
    "codecommit:GitPush",
    "codecommit:MergePullRequestByFastForward",
}


def _action_ok(allowed: str, requested: str) -> bool:
    if allowed in {"*", "codecommit:*"}:
        return requested in GIT_ACTIONS
    return allowed == requested


def _resource_ok(pattern: str, arn: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return arn.startswith(pattern[:-1])
    return pattern == arn


def _bool_ctx(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


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
            for key, expected in body.items():
                want = _bool_ctx(expected)
                have = _bool_ctx(ctx.get(key))
                if want is None or have is None or want != have:
                    return False
        elif op == "IpAddress":
            src = ctx.get("aws:SourceIp")
            if not src:
                return False
            addr = ipaddress.ip_address(str(src))
            matched = False
            for _key, cidr in body.items():
                nets = cidr if isinstance(cidr, list) else [cidr]
                for net in nets:
                    if addr in ipaddress.ip_network(str(net), strict=False):
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                return False
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
    deny = False
    allow = False
    for policy_id in catalog[principal].get("policies") or []:
        doc = policy_doc(policy_id)
        for stmt in doc.get("Statement") or []:
            if not _stmt_matches(stmt, action, arn, ctx):
                continue
            effect = str(stmt.get("Effect", "Allow")).lower()
            if effect == "deny":
                deny = True
            elif effect == "allow":
                allow = True
    if deny or not allow:
        raise CcError("AccessDenied")
