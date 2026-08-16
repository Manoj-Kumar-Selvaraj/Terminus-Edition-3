from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cc import home


def load_policy_document(policy_id: str) -> dict[str, Any]:
    path = home.policies_dir() / f"{policy_id}.json"
    if not path.exists():
        return {"Statement": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_principal_attachments() -> dict[str, Any]:
    path = home.principals_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def statements_for_principal(principal: str) -> list[dict[str, Any]]:
    attachments = load_principal_attachments()
    entry = attachments.get(principal)
    if entry is None:
        return []
    policies = entry.get("policies") or []
    out: list[dict[str, Any]] = []
    for pid in policies:
        doc = load_policy_document(pid)
        for stmt in doc.get("Statement") or []:
            enriched = dict(stmt)
            enriched["_policy_id"] = pid
            out.append(enriched)
    return out


def resource_matches(statement_resource: str, resource_arn: str, *, star_waives: bool) -> bool:
    """Broken path: when star_waives, any resource matches for Action *."""
    if star_waives:
        return True
    if statement_resource == resource_arn:
        return True
    if statement_resource.endswith("*"):
        prefix = statement_resource[:-1]
        return resource_arn.startswith(prefix)
    return False


def resource_matches_fixed(statement_resource: str, resource_arn: str) -> bool:
    if statement_resource == resource_arn:
        return True
    if statement_resource.endswith("*"):
        prefix = statement_resource[:-1]
        return resource_arn.startswith(prefix)
    return False


def repo_arn(repo: str) -> str:
    return f"arn:local:codecommit:local:000000000000:{repo}"


def list_policy_files() -> list[Path]:
    d = home.policies_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))
