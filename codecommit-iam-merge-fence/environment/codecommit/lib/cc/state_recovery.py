from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cc import home
from cc.util import dump_json, load_json, read_jsonl


def check_paths() -> dict[str, Any]:
    paths = {
        "principals": home.principals_path(),
        "approval_rules": home.approval_rules_path(),
        "pipelines": home.pipelines_path(),
        "webhooks": home.webhooks_path(),
        "catalog": home.catalog_path(),
        "prs": home.prs_path(),
        "triggers": home.triggers_path(),
        "audit": home.audit_path(),
        "outbox": home.outbox_path(),
    }
    return {k: {"path": str(v), "exists": v.exists()} for k, v in paths.items()}


def rebuild_catalog_from_repos() -> dict[str, Any]:
    repos: dict[str, Any] = {}
    for bare in home.repos_dir().glob("*.git"):
        name = bare.name[:-4] if bare.name.endswith(".git") else bare.name
        repos[name] = {
            "name": name,
            "default_branch": "main",
            "description": "recovered",
            "arn": f"arn:local:codecommit:local:000000000000:{name}",
        }
    dump_json(home.catalog_path(), {"repos": repos})
    return {"repos": sorted(repos)}


def compact_jsonl(path: Path) -> int:
    rows = read_jsonl(path)
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for row in reversed(rows):
        key = row.get("event_id") or id(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    out.reverse()
    path.write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in out),
        encoding="utf-8",
    )
    return len(out)


def health() -> dict[str, Any]:
    home.ensure_layout()
    return {"layout": True, "paths": check_paths(), "catalog": load_json(home.catalog_path(), {"repos": {}})}
