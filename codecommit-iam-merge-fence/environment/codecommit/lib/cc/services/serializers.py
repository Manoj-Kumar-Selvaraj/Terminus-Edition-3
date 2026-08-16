from __future__ import annotations
import json
from typing import Any

def dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(',', ':'), sort_keys=False)

def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)

def push_success(repo: str, ref: str, commit: str) -> dict[str, Any]:
    return {'ok': True, 'repo': repo, 'ref': ref, 'commit': commit}

def pr_success(pr_id: int, source: str, dest: str, source_commit: str) -> dict[str, Any]:
    return {'ok': True, 'pr_id': pr_id, 'source': source, 'dest': dest, 'source_commit': source_commit}

def approve_success(pr_id: int, approvals: list[str]) -> dict[str, Any]:
    return {'ok': True, 'pr_id': pr_id, 'approvals': sorted(approvals)}

def merge_success(pr_id: int, commit: str, fast_forward: bool) -> dict[str, Any]:
    return {'ok': True, 'pr_id': pr_id, 'commit': commit, 'fast_forward': fast_forward}
