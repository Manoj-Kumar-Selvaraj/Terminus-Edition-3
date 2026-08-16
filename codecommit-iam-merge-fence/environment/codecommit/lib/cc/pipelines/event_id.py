from __future__ import annotations

import hashlib
import uuid
from typing import Any

from cc import home
from cc.util import append_jsonl, full_ref, load_json, read_jsonl


def load_bindings() -> list[dict[str, Any]]:
    data = load_json(home.pipelines_path(), {"bindings": []})
    return list(data.get("bindings") or [])


def bindings_for(repo: str, ref: str, *, normalize: bool) -> list[dict[str, Any]]:
    ref_n = full_ref(ref) if normalize else ref
    out = []
    for b in load_bindings():
        b_ref = str(b.get("ref"))
        if normalize:
            b_ref = full_ref(b_ref)
        if b.get("repo") == repo and b_ref == ref_n:
            out.append(b)
    return out


def event_id(repo: str, ref: str, commit: str, pipeline: str, *, fixed: bool) -> str:
    if fixed:
        ref = full_ref(ref)
        preimage = f"{repo}|{ref}|{commit}|{pipeline}".encode()
        return hashlib.sha256(preimage).hexdigest()
    return str(uuid.uuid4())


def journal_rows() -> list[dict[str, Any]]:
    return read_jsonl(home.triggers_path())


def has_event(eid: str) -> bool:
    return any(r.get("event_id") == eid for r in journal_rows())


def append_delivery(row: dict[str, Any], *, fixed: bool) -> None:
    if fixed:
        keys = ["event_id", "repo", "ref", "commit", "pipeline", "status"]
        ordered = {k: row[k] for k in keys}
        append_jsonl(home.triggers_path(), ordered)
    else:
        # Broken: wrong key order / extra keys ok but missing pipeline sometimes
        broken = {
            "status": row.get("status"),
            "commit": row.get("commit"),
            "repo": row.get("repo"),
            "ref": row.get("ref"),
            "event_id": row.get("event_id"),
            "pipeline": row.get("pipeline"),
        }
        append_jsonl(home.triggers_path(), broken)
