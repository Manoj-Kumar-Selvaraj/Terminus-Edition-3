from __future__ import annotations

import hashlib
import json
from typing import Any

from cc.gitops import ref_commit
from cc.home import full_ref, pipeline_bindings, trigger_path


def _read_lines() -> list[dict[str, Any]]:
    path = trigger_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _event_id(repo: str, ref: str, commit: str, pipeline: str) -> str:
    return hashlib.sha256(f"{repo}|{ref}|{commit}|{pipeline}".encode()).hexdigest()


def deliver(repo: str, ref: str) -> dict[str, Any]:
    ref = full_ref(ref)
    bindings = [b for b in pipeline_bindings() if b["repo"] == repo and b["ref"] == ref]
    if not bindings:
        return {"ok": True, "delivered": [], "duplicate": False}
    commit = ref_commit(repo, ref)
    existing = _read_lines()
    known = {row["event_id"]: row for row in existing}
    path = trigger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    delivered = []
    all_dup = True
    for bind in bindings:
        eid = _event_id(repo, ref, commit, bind["pipeline"])
        if eid in known:
            delivered.append(known[eid])
            continue
        all_dup = False
        row = {
            "event_id": eid,
            "repo": repo,
            "ref": ref,
            "commit": commit,
            "pipeline": bind["pipeline"],
            "status": "delivered",
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        known[eid] = row
        delivered.append(row)
    return {"ok": True, "delivered": delivered, "duplicate": all_dup}
