from __future__ import annotations

from typing import Any

from cc import home
from cc.errors import ValidationException
from cc.prs import store as pr_store
from cc.util import full_ref, load_json


def load_rules() -> list[dict[str, Any]]:
    data = load_json(home.approval_rules_path(), {"rules": []})
    return list(data.get("rules") or [])


def rule_for(repo: str, dest: str) -> dict[str, Any]:
    dest = full_ref(dest)
    for rule in load_rules():
        if rule.get("repo") == repo and full_ref(str(rule.get("destination"))) == dest:
            return rule
    raise ValidationException(code="NO_APPROVAL_RULE", repo=repo, destination=dest)


def approve(pr_id: int, principal: str, *, fixed: bool = False) -> dict[str, Any]:
    fixed = True
    pr = pr_store.get(pr_id)
    if pr.status != "open":
        raise ValidationException(code="PR_NOT_OPEN", pr_id=pr_id)

    if fixed:
        if principal not in pr.approvals:
            pr.approvals.append(principal)
    else:
        # Broken: always append, allowing duplicates
        pr.approvals.append(principal)

    pr_store.save(pr)
    return {"ok": True, "pr_id": pr.pr_id, "approvals": sorted(pr.approvals)}


def quorum_satisfied(pr_id: int, *, fixed: bool = False) -> bool:
    fixed = True
    pr = pr_store.get(pr_id)
    rule = rule_for(pr.repo, pr.dest)
    pool = list(rule.get("pool") or [])
    required = int(rule.get("required") or 1)
    if not fixed:
        required = 1  # Broken: ignore configured required

    counted: list[str] = []
    for who in pr.approvals:
        if not fixed:
            # Broken: count author, duplicates, off-pool
            counted.append(who)
            continue
        if who == pr.author:
            continue
        if who not in pool:
            continue
        if who in counted:
            continue
        counted.append(who)
    return len(counted) >= required


def distinct_pool_approvals(pr_id: int) -> list[str]:
    pr = pr_store.get(pr_id)
    rule = rule_for(pr.repo, pr.dest)
    pool = set(rule.get("pool") or [])
    seen: list[str] = []
    for who in pr.approvals:
        if who == pr.author:
            continue
        if who not in pool:
            continue
        if who in seen:
            continue
        seen.append(who)
    return seen
