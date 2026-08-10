from __future__ import annotations

import json
import uuid
from typing import Any

from cc.home import full_ref, pipeline_bindings, trigger_path
from cc.gitops import ref_commit


def _read_lines() -> list[dict[str, Any]]:
    path = trigger_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def deliver(repo: str, ref: str) -> dict[str, Any]:
    ref = full_ref(ref)
    bindings = [b for b in pipeline_bindings() if b["repo"] == repo and b["ref"] == ref]
    commit = ref_commit(repo, ref)
    existing = _read_lines()
    delivered = []
    path = trigger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Broken: new event_id every call; always append.
    for bind in bindings:
        row = {
            "event_id": uuid.uuid4().hex,
            "repo": repo,
            "ref": ref,
            "commit": commit,
            "pipeline": bind["pipeline"],
            "status": "delivered",
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        delivered.append(row)
    _ = existing
    return {"ok": True, "delivered": delivered, "duplicate": False}
