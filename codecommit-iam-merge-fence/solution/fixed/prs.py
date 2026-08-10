from __future__ import annotations

import json
from typing import Any

from cc.errors import CcError
from cc.gitops import merge_ff, ref_commit
from cc.home import approval_rules, full_ref, pr_store_path


def _load() -> dict[str, Any]:
    path = pr_store_path()
    if not path.exists():
        return {"next_id": 1, "items": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(data: dict[str, Any]) -> None:
    path = pr_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create(repo: str, source: str, dest: str, author: str) -> dict[str, Any]:
    data = _load()
    pr_id = int(data["next_id"])
    data["next_id"] = pr_id + 1
    src_ref = full_ref(source)
    dst_ref = full_ref(dest)
    item = {
        "pr_id": pr_id,
        "repo": repo,
        "source": src_ref,
        "dest": dst_ref,
        "author": author,
        "approvals": [],
        "status": "open",
        "source_commit": ref_commit(repo, src_ref),
        "merged_commit": None,
    }
    data["items"][str(pr_id)] = item
    _save(data)
    return item


def get(repo: str, pr_id: int) -> dict[str, Any]:
    data = _load()
    item = data["items"].get(str(pr_id))
    if not item or item["repo"] != repo:
        raise CcError("ResourceNotFoundException", "PR_NOT_FOUND")
    return item


def approve(repo: str, pr_id: int, principal: str) -> dict[str, Any]:
    data = _load()
    key = str(pr_id)
    item = data["items"].get(key)
    if not item or item["repo"] != repo:
        raise CcError("ResourceNotFoundException", "PR_NOT_FOUND")
    if item["status"] != "open":
        raise CcError("ValidationException", "PR_NOT_OPEN")
    if principal not in item["approvals"]:
        item["approvals"].append(principal)
    _save(data)
    return item


def _quorum_ok(item: dict[str, Any]) -> bool:
    rules = [
        r
        for r in approval_rules()
        if r["repo"] == item["repo"] and r["destination"] == item["dest"]
    ]
    if not rules:
        raise CcError("ValidationException", "NO_APPROVAL_RULE")
    rule = rules[0]
    pool = set(rule["pool"])
    seen: list[str] = []
    for name in item.get("approvals") or []:
        if name == item["author"]:
            continue
        if name not in pool:
            continue
        if name not in seen:
            seen.append(name)
    return len(seen) >= int(rule["required"])


def merge(repo: str, pr_id: int) -> dict[str, Any]:
    data = _load()
    key = str(pr_id)
    item = data["items"].get(key)
    if not item or item["repo"] != repo:
        raise CcError("ResourceNotFoundException", "PR_NOT_FOUND")
    if item["status"] != "open":
        raise CcError("ValidationException", "PR_NOT_OPEN")
    if not _quorum_ok(item):
        raise CcError("ValidationException", "APPROVAL_QUORUM")
    commit = merge_ff(repo, item["source"], item["dest"])
    item["status"] = "merged"
    item["merged_commit"] = commit
    item["source_commit"] = commit
    _save(data)
    return item
