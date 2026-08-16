from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from cc.iam import actions, policy
from cc.iam.eval import explain
from cc.policy_admin import list_policies, principals, read_policy
from cc.util import full_ref


def statement_index() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid in list_policies():
        doc = read_policy(pid)
        for i, stmt in enumerate(doc.get("Statement") or []):
            rows.append(
                {
                    "policy": pid,
                    "index": i,
                    "sid": stmt.get("Sid"),
                    "effect": stmt.get("Effect"),
                    "action": stmt.get("Action"),
                    "resource": stmt.get("Resource"),
                    "has_condition": bool(stmt.get("Condition")),
                    "condition_ops": sorted((stmt.get("Condition") or {}).keys()),
                }
            )
    return rows


def action_coverage() -> dict[str, list[str]]:
    cov: dict[str, list[str]] = defaultdict(list)
    for row in statement_index():
        act = str(row.get("action"))
        if act in ("*", "codecommit:*"):
            for a in actions.ALL_ACTIONS:
                cov[a].append(str(row["policy"]))
        else:
            cov[act].append(str(row["policy"]))
    return {k: sorted(set(v)) for k, v in cov.items()}


def principals_by_action(action: str) -> list[str]:
    out: list[str] = []
    data = principals()
    for name, entry in data.items():
        for pid in entry.get("policies") or []:
            doc = read_policy(pid)
            for stmt in doc.get("Statement") or []:
                sa = str(stmt.get("Action"))
                if sa in (action, "*", "codecommit:*"):
                    out.append(name)
                    break
    return sorted(set(out))


def simulate_grid(
    principal: str,
    repo: str,
    refs: list[str],
    *,
    mfa: bool,
    source_ip: str,
    fixed: bool = False,
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    for ref in refs:
        for action in actions.ALL_ACTIONS:
            cells.append(
                explain(
                    principal,
                    action,
                    repo,
                    full_ref(ref),
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=fixed,
                )
            )
    allowed = sum(1 for c in cells if c.get("allowed"))
    return {"cells": cells, "allowed": allowed, "denied": len(cells) - allowed}


def effect_histogram() -> dict[str, int]:
    return dict(Counter(str(r.get("effect")) for r in statement_index()))


def condition_histogram() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in statement_index():
        for op in row.get("condition_ops") or []:
            counts[str(op)] += 1
    return dict(counts)


def orphan_policies() -> list[str]:
    attached: set[str] = set()
    for entry in principals().values():
        attached.update(entry.get("policies") or [])
    return [p for p in list_policies() if p not in attached]


def duplicate_sids() -> list[dict[str, Any]]:
    seen: dict[str, list[str]] = defaultdict(list)
    for row in statement_index():
        sid = row.get("sid")
        if sid:
            seen[str(sid)].append(str(row["policy"]))
    return [{"sid": k, "policies": v} for k, v in seen.items() if len(v) > 1]


def resource_patterns() -> list[str]:
    return sorted({str(r.get("resource")) for r in statement_index()})


def attachment_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, entry in sorted(principals().items()):
        rows.append({"principal": name, "policies": list(entry.get("policies") or []), "count": len(entry.get("policies") or [])})
    return rows


def full_iam_report(principal: str, repo: str) -> dict[str, Any]:
    return {
        "statements": statement_index(),
        "coverage": action_coverage(),
        "effects": effect_histogram(),
        "conditions": condition_histogram(),
        "orphans": orphan_policies(),
        "resources": resource_patterns(),
        "attachments": attachment_matrix(),
        "grid_mfa_office": simulate_grid(principal, repo, ["main", "dev/alice", "release"], mfa=True, source_ip="10.8.12.4", fixed=True),
        "grid_no_mfa": simulate_grid(principal, repo, ["main"], mfa=False, source_ip="10.8.12.4", fixed=True),
    }
