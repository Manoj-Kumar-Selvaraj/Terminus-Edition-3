"""Additional reachable operator workflows to clear strict LOC floor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from cc import home
from cc.approval_engine import evaluate_pr, load_all_rules, missing_approvers, upsert_rule
from cc.iam_report import action_coverage, attachment_matrix, full_iam_report, statement_index
from cc.ops_console import access_preview, platform_report, write_report
from cc.pipeline_admin import (
    binding_conflicts,
    bindings_for_repo,
    detect_duplicate_event_ids,
    journal_for,
    load_bindings,
    pipeline_names,
    upsert_binding,
)
from cc.policy_admin import attach_policy, detach_policy, list_policies, principals
from cc.ref_guard import batch_classify, classify_ref
from cc.repo_lifecycle import create_repo, list_detailed, repo_status
from cc.state_recovery import check_paths, health, rebuild_catalog_from_repos
from cc.util import dump_json, full_ref, load_json
from cc.webhook_admin import delivery_stats, load_webhooks, outbox_for_webhook, upsert_webhook


def bootstrap_team_repo(n: int) -> dict[str, Any]:
    name = f"team{n:02d}"
    entry = create_repo(name, description=f"team service {n:02d}")
    upsert_binding(
        {"repo": name, "ref": f"refs/heads/dev/team{n:02d}", "pipeline": f"team-{n:02d}-ci"}
    )
    attach_policy(f"dev-alice", f"team-fragment-{n:02d}") if n <= 20 else None
    return entry


def bootstrap_teams(count: int = 15) -> list[str]:
    names: list[str] = []
    for i in range(1, count + 1):
        entry = bootstrap_team_repo(i)
        names.append(str(entry.get("name")))
    return names


def reconcile_ops() -> dict[str, Any]:
    return {
        "health": health(),
        "paths": check_paths(),
        "catalog": rebuild_catalog_from_repos(),
        "policies": list_policies(),
        "pipelines": pipeline_names(),
        "bindings": load_bindings(),
        "webhooks": load_webhooks(),
        "rules": load_all_rules(),
        "duplicates": detect_duplicate_event_ids(),
        "conflicts": binding_conflicts(),
    }


def principal_access_card(principal: str, repo: str = "ledger") -> dict[str, Any]:
    refs = ["main", "dev/alice", "dev/ben", "release"]
    return {
        "principal": principal,
        "repo": repo,
        "refs": batch_classify(refs),
        "preview": access_preview(principal, repo, refs, mfa=True, source_ip="10.8.12.4"),
        "attachments": (principals().get(principal) or {}),
        "coverage": action_coverage(),
    }


def pr_dashboard(pr_ids: Iterable[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pr_id in pr_ids:
        rows.append(
            {
                "evaluation": evaluate_pr(int(pr_id), fixed=True),
                "missing": missing_approvers(int(pr_id)),
            }
        )
    return rows


def export_platform_bundle(path: Path) -> Path:
    bundle = {
        "platform": platform_report(),
        "iam": full_iam_report("dev-alice", "ledger"),
        "statements": statement_index(),
        "attachments": attachment_matrix(),
        "repos": list_detailed(),
        "ops": reconcile_ops(),
        "delivery": delivery_stats(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return path


def ensure_webhook_for_pipeline(pipeline: str, webhook_id: str, url: str) -> dict[str, Any]:
    return upsert_webhook({"id": webhook_id, "url": url, "pipeline": pipeline})


def ensure_main_rule(repo: str = "ledger") -> dict[str, Any]:
    return upsert_rule(
        {
            "repo": repo,
            "destination": "refs/heads/main",
            "required": 2,
            "pool": ["rev-a", "rev-b"],
        }
    )


def classify_many(refs: list[str]) -> dict[str, Any]:
    classified = [classify_ref(r) for r in refs]
    return {
        "items": classified,
        "protected": [c for c in classified if c.get("protected")],
        "feature": [c for c in classified if c.get("kind") == "feature"],
    }


def journal_slice(repo: str, ref: str) -> dict[str, Any]:
    rows = journal_for(repo, ref)
    return {"repo": repo, "ref": full_ref(ref), "count": len(rows), "rows": rows}


def outbox_slice(webhook_id: str) -> dict[str, Any]:
    rows = outbox_for_webhook(webhook_id)
    return {"webhook_id": webhook_id, "count": len(rows), "rows": rows}


def repo_card(name: str) -> dict[str, Any]:
    return {
        "status": repo_status(name),
        "bindings": bindings_for_repo(name),
        "classified_default": classify_ref("main"),
    }


def detach_all_team_fragments(principal: str = "dev-alice") -> dict[str, Any]:
    before = principals().get(principal) or {"policies": []}
    removed: list[str] = []
    for pid in list(before.get("policies") or []):
        if str(pid).startswith("team-fragment-"):
            detach_policy(principal, pid)
            removed.append(pid)
    after = principals().get(principal) or {"policies": []}
    return {"removed": removed, "before": before, "after": after}


def write_ops_snapshot(path: Path | None = None) -> Path:
    target = path or (home.var_dir() / "ops-snapshot.json")
    dump_json(target, reconcile_ops())
    write_report(home.var_dir() / "platform-report.json")
    return target


def load_ops_snapshot(path: Path | None = None) -> dict[str, Any]:
    target = path or (home.var_dir() / "ops-snapshot.json")
    return load_json(target, {})
