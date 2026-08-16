from __future__ import annotations

import json
from typing import Any

from cc import home
from cc.services.validators import validate_principal
from cc.util import dump_json, load_json


def list_policies() -> list[str]:
    return sorted(p.stem for p in home.policies_dir().glob("*.json"))


def read_policy(policy_id: str) -> dict[str, Any]:
    path = home.policies_dir() / f"{policy_id}.json"
    if not path.exists():
        raise FileNotFoundError(policy_id)
    return json.loads(path.read_text(encoding="utf-8"))


def write_policy(policy_id: str, document: dict[str, Any]) -> None:
    if "Statement" not in document or not isinstance(document["Statement"], list):
        raise ValueError("policy requires Statement list")
    for stmt in document["Statement"]:
        for key in ("Effect", "Action", "Resource"):
            if key not in stmt:
                raise ValueError(f"statement missing {key}")
    path = home.policies_dir() / f"{policy_id}.json"
    dump_json(path, document)


def attach_policy(principal: str, policy_id: str) -> dict[str, Any]:
    validate_principal(principal)
    data = load_json(home.principals_path(), {})
    entry = data.setdefault(principal, {"policies": [], "roles": []})
    pols = list(entry.get("policies") or [])
    if policy_id not in pols:
        pols.append(policy_id)
    entry["policies"] = pols
    data[principal] = entry
    dump_json(home.principals_path(), data)
    return entry


def detach_policy(principal: str, policy_id: str) -> dict[str, Any]:
    validate_principal(principal)
    data = load_json(home.principals_path(), {})
    entry = data.get(principal) or {"policies": [], "roles": []}
    entry["policies"] = [p for p in (entry.get("policies") or []) if p != policy_id]
    data[principal] = entry
    dump_json(home.principals_path(), data)
    return entry


def principals() -> dict[str, Any]:
    return load_json(home.principals_path(), {})


def diff_attachments(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    added = {k: after[k] for k in after.keys() - before.keys()}
    removed = {k: before[k] for k in before.keys() - after.keys()}
    changed = {}
    for k in before.keys() & after.keys():
        if before[k] != after[k]:
            changed[k] = {"before": before[k], "after": after[k]}
    return {"added": added, "removed": removed, "changed": changed}
