"""Detect drift between catalog, filesystem repos, bindings, and live tips."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cc import home
from cc.pipeline_admin import bindings_for_repo, load_bindings
from cc.repos import catalog, gitops
from cc.util import full_ref, load_json
from cc.webhook_admin import load_webhooks


def catalog_vs_disk() -> dict[str, Any]:
    named = set(catalog.list_repos())
    disk = {p.name for p in home.repos_dir().glob("*") if p.is_dir()}
    return {
        "only_catalog": sorted(named - disk),
        "only_disk": sorted(disk - named),
        "both": sorted(named & disk),
    }


def binding_repo_orphans() -> list[dict[str, Any]]:
    named = set(catalog.list_repos())
    return [b for b in load_bindings() if str(b.get("repo")) not in named]


def webhook_pipeline_orphans() -> list[dict[str, Any]]:
    pipelines = {str(b.get("pipeline")) for b in load_bindings()}
    return [w for w in load_webhooks() if str(w.get("pipeline")) not in pipelines]


def tip_mismatch(repo: str, ref: str, expected: str | None) -> dict[str, Any]:
    tip = None
    err = None
    try:
        tip = gitops.ref_commit(repo, full_ref(ref))
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    return {
        "repo": repo,
        "ref": full_ref(ref),
        "tip": tip,
        "expected": expected,
        "match": tip == expected if expected and tip else None,
        "error": err,
    }


def open_pr_tip_drift() -> list[dict[str, Any]]:
    from cc.prs import store as pr_store

    rows: list[dict[str, Any]] = []
    for pr in pr_store.list_open():
        live = tip_mismatch(pr.repo, pr.source, pr.source_commit)
        if live.get("tip") and live.get("tip") != pr.source_commit:
            rows.append(
                {
                    "pr_id": pr.pr_id,
                    "repo": pr.repo,
                    "stored": pr.source_commit,
                    "live": live.get("tip"),
                }
            )
    return rows


def default_branch_drift() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in catalog.list_repos():
        meta = catalog.get_repo(name) or {}
        expected = str(meta.get("default_branch") or "main")
        head = tip_mismatch(name, expected, None)
        rows.append(
            {
                "repo": name,
                "default_branch": expected,
                "tip": head.get("tip"),
                "error": head.get("error"),
            }
        )
    return rows


def binding_coverage_by_repo() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in catalog.list_repos():
        bindings = bindings_for_repo(name)
        rows.append(
            {
                "repo": name,
                "binding_count": len(bindings),
                "refs": sorted({full_ref(str(b.get("ref"))) for b in bindings}),
            }
        )
    return rows


def principals_doc_drift() -> dict[str, Any]:
    doc = load_json(home.principals_path(), {"principals": {}})
    principals = doc.get("principals") or doc
    if isinstance(principals, list):
        return {"shape": "list", "count": len(principals)}
    if "principals" in doc:
        principals = doc.get("principals") or {}
    return {
        "shape": "map",
        "count": len(principals) if isinstance(principals, dict) else 0,
        "names": sorted(principals) if isinstance(principals, dict) else [],
    }


def full_drift_report() -> dict[str, Any]:
    return {
        "catalog_vs_disk": catalog_vs_disk(),
        "binding_orphans": binding_repo_orphans(),
        "webhook_orphans": webhook_pipeline_orphans(),
        "open_pr_tip_drift": open_pr_tip_drift(),
        "default_branch_drift": default_branch_drift(),
        "binding_coverage": binding_coverage_by_repo(),
        "principals_doc": principals_doc_drift(),
    }


def write_drift_report(path: Path | None = None) -> Path:
    import json

    target = path or (home.var_dir() / "drift-report.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(full_drift_report(), indent=2) + "\n", encoding="utf-8")
    return target
