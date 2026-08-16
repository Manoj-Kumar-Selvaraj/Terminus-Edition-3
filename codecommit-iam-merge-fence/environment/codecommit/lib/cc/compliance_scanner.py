"""Compliance scanning across IAM, approvals, pipelines, and delivery state."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from cc import home
from cc.approval_engine import load_all_rules
from cc.audit import query as audit_query
from cc.iam_report import action_coverage, attachment_matrix, statement_index
from cc.pipeline_admin import binding_conflicts, load_bindings, pipeline_names
from cc.policy_admin import list_policies, principals, read_policy
from cc.prs import store as pr_store
from cc.ref_guard import classify_ref
from cc.repos import catalog
from cc.util import full_ref
from cc.webhook_admin import delivery_stats, load_webhooks

PROTECTED_KINDS = {"main", "release"}


def _policy_effects() -> Counter[str]:
    counts: Counter[str] = Counter()
    for pid in list_policies():
        for stmt in read_policy(pid).get("Statement") or []:
            counts[str(stmt.get("Effect", "Allow"))] += 1
    return counts


def policies_missing_sid() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid in list_policies():
        for idx, stmt in enumerate(read_policy(pid).get("Statement") or []):
            if not stmt.get("Sid"):
                rows.append({"policy": pid, "index": idx, "action": stmt.get("Action")})
    return rows


def unprotected_main_bindings() -> list[dict[str, Any]]:
    bad: list[dict[str, Any]] = []
    for b in load_bindings():
        ref = full_ref(str(b.get("ref") or ""))
        kind = classify_ref(ref).get("kind")
        if kind in PROTECTED_KINDS and not b.get("pipeline"):
            bad.append(dict(b))
    return bad


def approval_rules_without_pool() -> list[dict[str, Any]]:
    return [r for r in load_all_rules() if not (r.get("pool") or [])]


def approval_rules_required_lt_two() -> list[dict[str, Any]]:
    return [r for r in load_all_rules() if int(r.get("required") or 0) < 2]


def open_prs_missing_rule() -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    rules = {(r.get("repo"), full_ref(str(r.get("destination")))) for r in load_all_rules()}
    for pr in pr_store.list_open():
        key = (pr.repo, full_ref(pr.dest))
        if key not in rules:
            missing.append({"pr_id": pr.pr_id, "repo": pr.repo, "dest": pr.dest})
    return missing


def principals_without_policies() -> list[str]:
    empty: list[str] = []
    for name, body in principals().items():
        if not (body or {}).get("policies"):
            empty.append(name)
    return sorted(empty)


def webhook_without_pipeline() -> list[dict[str, Any]]:
    return [w for w in load_webhooks() if not w.get("pipeline")]


def denied_ratio() -> dict[str, Any]:
    summary = audit_query.summary()
    total = int(summary.get("total") or 0)
    denied = int(summary.get("denied") or 0)
    return {"total": total, "denied": denied, "ratio": (denied / total) if total else 0.0}


def resource_star_statements() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in statement_index():
        resource = str(row.get("resource") or "")
        if resource.endswith("*") or resource == "*":
            rows.append(row)
    return rows


def scan_findings() -> dict[str, Any]:
    return {
        "effects": dict(_policy_effects()),
        "missing_sid": policies_missing_sid(),
        "unprotected_main_bindings": unprotected_main_bindings(),
        "rules_without_pool": approval_rules_without_pool(),
        "rules_required_lt_two": approval_rules_required_lt_two(),
        "open_prs_missing_rule": open_prs_missing_rule(),
        "principals_without_policies": principals_without_policies(),
        "webhook_without_pipeline": webhook_without_pipeline(),
        "denied_ratio": denied_ratio(),
        "resource_star": resource_star_statements(),
        "binding_conflicts": binding_conflicts(),
        "coverage": action_coverage(),
        "attachments": attachment_matrix(),
        "delivery": delivery_stats(),
        "repos": catalog.list_repos(),
        "pipelines": pipeline_names(),
    }


def score_findings(findings: dict[str, Any] | None = None) -> dict[str, Any]:
    f = findings or scan_findings()
    score = 100
    deductions: list[dict[str, Any]] = []
    checks = [
        ("missing_sid", 2),
        ("unprotected_main_bindings", 10),
        ("rules_without_pool", 8),
        ("rules_required_lt_two", 6),
        ("open_prs_missing_rule", 5),
        ("principals_without_policies", 4),
        ("webhook_without_pipeline", 3),
        ("resource_star", 1),
        ("binding_conflicts", 7),
    ]
    for key, weight in checks:
        items = f.get(key) or []
        if isinstance(items, list) and items:
            hit = min(len(items) * weight, weight * 5)
            score -= hit
            deductions.append({"check": key, "count": len(items), "deduction": hit})
    ratio = float((f.get("denied_ratio") or {}).get("ratio") or 0.0)
    if ratio > 0.5:
        score -= 5
        deductions.append({"check": "denied_ratio", "ratio": ratio, "deduction": 5})
    return {"score": max(score, 0), "deductions": deductions, "findings": f}


def write_compliance_report(path: Path | None = None) -> Path:
    import json

    target = path or (home.var_dir() / "compliance-report.json")
    body = score_findings()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return target
