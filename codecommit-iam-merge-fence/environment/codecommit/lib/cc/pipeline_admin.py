from __future__ import annotations

from typing import Any

from cc import home
from cc.pipelines import event_id as eid_mod
from cc.services.validators import validate_pipeline_binding
from cc.util import dump_json, full_ref, load_json


def load_bindings() -> list[dict[str, Any]]:
    return list(load_json(home.pipelines_path(), {"bindings": []}).get("bindings") or [])


def save_bindings(bindings: list[dict[str, Any]]) -> None:
    cleaned = [validate_pipeline_binding(b) for b in bindings]
    dump_json(home.pipelines_path(), {"bindings": cleaned})


def upsert_binding(binding: dict[str, Any]) -> dict[str, Any]:
    binding = validate_pipeline_binding(binding)
    rows = load_bindings()
    out: list[dict[str, Any]] = []
    replaced = False
    for row in rows:
        if row.get("repo") == binding["repo"] and full_ref(str(row.get("ref"))) == binding["ref"]:
            out.append(binding)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(binding)
    save_bindings(out)
    return binding


def remove_binding(repo: str, ref: str) -> int:
    ref = full_ref(ref)
    before = load_bindings()
    after = [b for b in before if not (b.get("repo") == repo and full_ref(str(b.get("ref"))) == ref)]
    save_bindings(after)
    return len(before) - len(after)


def bindings_for_repo(repo: str) -> list[dict[str, Any]]:
    return [b for b in load_bindings() if b.get("repo") == repo]


def journal_for(repo: str, ref: str | None = None) -> list[dict[str, Any]]:
    rows = eid_mod.journal_rows()
    out = [r for r in rows if r.get("repo") == repo]
    if ref is not None:
        ref = full_ref(ref)
        out = [r for r in out if full_ref(str(r.get("ref"))) == ref]
    return out


def unique_event_ids() -> list[str]:
    return sorted({str(r.get("event_id")) for r in eid_mod.journal_rows()})


def detect_duplicate_event_ids() -> list[str]:
    seen: set[str] = set()
    dups: set[str] = set()
    for row in eid_mod.journal_rows():
        eid = str(row.get("event_id"))
        if eid in seen:
            dups.add(eid)
        seen.add(eid)
    return sorted(dups)


def pipeline_names() -> list[str]:
    return sorted({str(b.get("pipeline")) for b in load_bindings()})


def binding_conflicts() -> list[dict[str, Any]]:
    """Same repo/ref mapped to multiple pipelines is allowed; report multiplicity."""
    counts: dict[tuple[str, str], list[str]] = {}
    for b in load_bindings():
        key = (str(b.get("repo")), full_ref(str(b.get("ref"))))
        counts.setdefault(key, []).append(str(b.get("pipeline")))
    return [
        {"repo": k[0], "ref": k[1], "pipelines": v}
        for k, v in counts.items()
        if len(v) > 1
    ]
