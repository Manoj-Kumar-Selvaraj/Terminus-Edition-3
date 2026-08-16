"""Additional reachable control-plane helpers for reporting and admin workflows."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from cc import home
from cc.approval_engine import evaluate_pr, load_all_rules, missing_approvers
from cc.audit import query as audit_query
from cc.batch_ops import DEFAULT_ACTIONS, explain_matrix
from cc.config_schema import validate_all
from cc.pipelines import event_id as eid_mod
from cc.policy_admin import list_policies, principals, read_policy
from cc.prs import store as pr_store
from cc.ref_guard import batch_classify
from cc.repos import catalog
from cc.state_recovery import health
from cc.util import load_json
from cc.webhooks import outbox


def inventory_policies() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid in list_policies():
        doc = read_policy(pid)
        stmts = list(doc.get("Statement") or [])
        rows.append(
            {
                "id": pid,
                "statements": len(stmts),
                "effects": sorted({str(s.get("Effect")) for s in stmts}),
                "actions": sorted({str(s.get("Action")) for s in stmts}),
            }
        )
    return rows


def inventory_principals() -> list[dict[str, Any]]:
    data = principals()
    return [
        {"name": name, "policies": list((entry or {}).get("policies") or []), "roles": list((entry or {}).get("roles") or [])}
        for name, entry in sorted(data.items())
    ]


def inventory_repos() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in catalog.list_repos():
        entry = catalog.get_repo(name) or {"name": name}
        out.append(entry)
    return out


def open_pr_report() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pr in pr_store.list_open():
        rows.append(
            {
                "evaluation": evaluate_pr(pr.pr_id, fixed=True),
                "missing": missing_approvers(pr.pr_id),
                "status": pr.status,
            }
        )
    return rows


def config_validation_report() -> dict[str, list[str]]:
    return validate_all(
        load_json(home.principals_path(), {}),
        load_json(home.approval_rules_path(), {"rules": []}),
        load_json(home.pipelines_path(), {"bindings": []}),
        load_json(home.webhooks_path(), {"webhooks": []}),
    )


def journal_by_pipeline() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in eid_mod.journal_rows():
        counts[str(row.get("pipeline"))] += 1
    return dict(counts)


def outbox_by_webhook() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in outbox.all_rows():
        counts[str(row.get("webhook_id"))] += 1
    return dict(counts)


def access_preview(principal: str, repo: str, refs: Iterable[str], *, mfa: bool, source_ip: str) -> dict[str, Any]:
    refs_list = list(refs)
    return {
        "principal": principal,
        "repo": repo,
        "refs": batch_classify(refs_list),
        "matrix": explain_matrix(
            principal,
            repo,
            refs_list,
            DEFAULT_ACTIONS,
            mfa=mfa,
            source_ip=source_ip,
            fixed=True,
        ),
    }


def platform_report() -> dict[str, Any]:
    return {
        "health": health(),
        "policies": inventory_policies(),
        "principals": inventory_principals(),
        "repos": inventory_repos(),
        "rules": load_all_rules(),
        "open_prs": open_pr_report(),
        "config_errors": config_validation_report(),
        "audit": audit_query.summary(),
        "journal_by_pipeline": journal_by_pipeline(),
        "outbox_by_webhook": outbox_by_webhook(),
    }


def write_report(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(platform_report(), indent=2) + "\n", encoding="utf-8")
    return path


def compare_principals(a: str, b: str) -> dict[str, Any]:
    data = principals()
    pa = set((data.get(a) or {}).get("policies") or [])
    pb = set((data.get(b) or {}).get("policies") or [])
    return {
        "a": a,
        "b": b,
        "only_a": sorted(pa - pb),
        "only_b": sorted(pb - pa),
        "shared": sorted(pa & pb),
    }


def find_policies_granting(action: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for pid in list_policies():
        doc = read_policy(pid)
        for idx, stmt in enumerate(doc.get("Statement") or []):
            if str(stmt.get("Action")) in (action, "*", "codecommit:*"):
                hits.append({"policy": pid, "index": idx, "effect": stmt.get("Effect"), "resource": stmt.get("Resource")})
    return hits


def summarize_denies() -> list[dict[str, Any]]:
    return audit_query.denied_only()[-50:]


def webhook_pending_summary() -> dict[str, Any]:
    pending = outbox.pending()
    return {
        "count": len(pending),
        "event_ids": [p.get("event_id") for p in pending],
        "webhooks": sorted({str(p.get("webhook_id")) for p in pending}),
    }
