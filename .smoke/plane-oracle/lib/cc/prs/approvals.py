"""Approval-rule lookup and quorum accounting."""

from __future__ import annotations

from typing import Any

from cc.errors import ValidationException
from cc.home import approval_rules
from cc.models import ApprovalRule, PullRequest
from cc.util import glob_match, unique


def rules_for_repo(repo: str) -> list[ApprovalRule]:
    """Rules configured for one repository, in file order."""
    return [
        ApprovalRule.from_dict(body) for body in approval_rules() if body.get("repo") == repo
    ]


def find_rule(repo: str, dest: str) -> ApprovalRule | None:
    """First rule whose destination pattern covers this pull request."""
    for rule in rules_for_repo(repo):
        if rule.dest == dest or glob_match(rule.dest, dest):
            return rule
    return None


def require_rule(repo: str, dest: str) -> ApprovalRule:
    """Rule governing this destination, or a control-plane error."""
    rule = find_rule(repo, dest)
    if rule is None:
        raise ValidationException(
            "NO_APPROVAL_RULE", f"no approval rule covers {repo} {dest}", repo=repo, dest=dest
        )
    return rule


def required_count(rule: ApprovalRule) -> int:
    """Number of counting approvals this destination needs."""
    return max(1, int(rule.required))


def counted_approvals(request: PullRequest, rule: ApprovalRule) -> list[str]:
    """Stamps that count toward this pull request's quorum.

    Only distinct pool members count, and the author's own stamp never does.
    """
    pool = set(rule.pool)
    counted: list[str] = []
    for name in unique(request.approvals):
        if name == request.author:
            continue
        if pool and name not in pool:
            continue
        counted.append(name)
    return counted


def ignored_approvals(request: PullRequest, rule: ApprovalRule) -> list[str]:
    """Stamps present on the request that do not count toward quorum."""
    counted = set(counted_approvals(request, rule))
    return sorted({name for name in request.approvals if name not in counted})


def status(request: PullRequest) -> dict[str, Any]:
    """Quorum state of one pull request."""
    rule = require_rule(request.repo, request.dest)
    counted = counted_approvals(request, rule)
    required = required_count(rule)
    return {
        "rule_id": rule.rule_id,
        "required": required,
        "counted": sorted(unique(counted)),
        "ignored": ignored_approvals(request, rule),
        "pool": list(rule.pool),
        "satisfied": len(unique(counted)) >= required,
        "missing": max(0, required - len(unique(counted))),
    }


def assert_quorum(request: PullRequest) -> dict[str, Any]:
    """Raise unless the pull request carries enough counting approvals."""
    state = status(request)
    if not state["satisfied"]:
        raise ValidationException(
            "APPROVAL_QUORUM",
            f"pull request {request.pr_id} has {len(state['counted'])} of "
            f"{state['required']} required approvals",
            rule_id=state["rule_id"],
            required=state["required"],
            counted=len(state["counted"]),
        )
    return state
