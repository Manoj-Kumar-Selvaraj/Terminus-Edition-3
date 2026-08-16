"""Branch protection rules consulted on push and merge."""

from __future__ import annotations

from typing import Any

from cc import home
from cc.errors import ValidationException
from cc.util import dump_json, full_ref, load_json


DEFAULT_RULES = [
    {
        "repo": "ledger",
        "pattern": "refs/heads/main",
        "require_linear_history": True,
        "require_lease": True,
    },
    {
        "repo": "ledger",
        "pattern": "refs/heads/release",
        "require_linear_history": True,
        "require_lease": True,
    },
]


def protection_path():
    return home.ops_dir() / "branch-protection.json"


def load_rules() -> list[dict[str, Any]]:
    doc = load_json(protection_path(), {"rules": DEFAULT_RULES})
    return list(doc.get("rules") or DEFAULT_RULES)


def save_rules(rules: list[dict[str, Any]]) -> None:
    dump_json(protection_path(), {"rules": rules})


def matching_rules(repo: str, ref: str) -> list[dict[str, Any]]:
    ref_n = full_ref(ref)
    hits: list[dict[str, Any]] = []
    for rule in load_rules():
        if rule.get("repo") != repo:
            continue
        pattern = full_ref(str(rule.get("pattern") or ""))
        if pattern.endswith("/*"):
            if ref_n.startswith(pattern[:-1]):
                hits.append(rule)
        elif pattern == ref_n:
            hits.append(rule)
    return hits


def assert_push_allowed(repo: str, ref: str, *, principal: str) -> None:
    for rule in matching_rules(repo, ref):
        if rule.get("block_direct_push"):
            raise ValidationException(code="PROTECTED_REF_PUSH", repo=repo, ref=full_ref(ref))
        allow = rule.get("allowed_push_principals")
        if allow is not None and principal not in allow:
            raise ValidationException(code="PROTECTED_REF_PUSH", repo=repo, ref=full_ref(ref))


def assert_merge_allowed(repo: str, ref: str, *, principal: str) -> dict[str, Any]:
    rules = matching_rules(repo, ref)
    if not rules:
        return {"protected": False, "require_lease": False, "require_linear_history": False}
    require_lease = any(bool(r.get("require_lease")) for r in rules)
    require_linear = any(bool(r.get("require_linear_history")) for r in rules)
    for rule in rules:
        allow = rule.get("allowed_merge_principals")
        if allow is not None and principal not in allow:
            raise ValidationException(code="PROTECTED_REF_MERGE", repo=repo, ref=full_ref(ref))
    return {
        "protected": True,
        "require_lease": require_lease,
        "require_linear_history": require_linear,
        "rules": rules,
    }


def summarize() -> dict[str, Any]:
    rules = load_rules()
    return {
        "count": len(rules),
        "repos": sorted({str(r.get("repo")) for r in rules}),
        "lease_required": sum(1 for r in rules if r.get("require_lease")),
        "linear_required": sum(1 for r in rules if r.get("require_linear_history")),
    }
