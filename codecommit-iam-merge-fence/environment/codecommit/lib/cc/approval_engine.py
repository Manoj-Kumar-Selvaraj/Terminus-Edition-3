from __future__ import annotations

from typing import Any

from cc import home
from cc.prs import approvals, store as pr_store
from cc.services.validators import validate_approval_rule
from cc.util import dump_json, full_ref, load_json


def load_all_rules() -> list[dict[str, Any]]:
    return list(load_json(home.approval_rules_path(), {"rules": []}).get("rules") or [])


def save_rules(rules: list[dict[str, Any]]) -> None:
    cleaned = [validate_approval_rule(r) for r in rules]
    dump_json(home.approval_rules_path(), {"rules": cleaned})


def upsert_rule(rule: dict[str, Any]) -> dict[str, Any]:
    rule = validate_approval_rule(rule)
    rules = load_all_rules()
    out: list[dict[str, Any]] = []
    replaced = False
    for r in rules:
        if r.get("repo") == rule["repo"] and full_ref(str(r.get("destination"))) == rule["destination"]:
            out.append(rule)
            replaced = True
        else:
            out.append(r)
    if not replaced:
        out.append(rule)
    save_rules(out)
    return rule


def evaluate_pr(pr_id: int, *, fixed: bool = False) -> dict[str, Any]:
    pr = pr_store.get(pr_id)
    rule = approvals.rule_for(pr.repo, pr.dest)
    distinct = approvals.distinct_pool_approvals(pr_id) if fixed else list(pr.approvals)
    required = int(rule.get("required") or 1) if fixed else 1
    return {
        "pr_id": pr_id,
        "author": pr.author,
        "approvals": list(pr.approvals),
        "distinct_pool": distinct,
        "required": required,
        "pool": list(rule.get("pool") or []),
        "satisfied": approvals.quorum_satisfied(pr_id, fixed=fixed),
    }


def missing_approvers(pr_id: int) -> list[str]:
    pr = pr_store.get(pr_id)
    rule = approvals.rule_for(pr.repo, pr.dest)
    pool = list(rule.get("pool") or [])
    have = set(approvals.distinct_pool_approvals(pr_id))
    return [p for p in pool if p not in have and p != pr.author]
