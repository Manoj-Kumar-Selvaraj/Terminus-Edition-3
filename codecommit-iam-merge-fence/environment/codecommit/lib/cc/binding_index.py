"""Pipeline binding index with normalization and conflict detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cc import home
from cc.util import full_ref, load_json


def load_bindings() -> list[dict[str, Any]]:
    data = load_json(home.pipelines_path(), {"bindings": []})
    return list(data.get("bindings") or [])


def indexed(normalize: bool = True) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for b in load_bindings():
        repo = str(b.get("repo") or "")
        ref = full_ref(str(b.get("ref") or "")) if normalize else str(b.get("ref") or "")
        out[(repo, ref)].append(b)
    return dict(out)


def lookup(repo: str, ref: str, *, normalize: bool) -> list[dict[str, Any]]:
    ref_n = full_ref(ref) if normalize else ref
    hits: list[dict[str, Any]] = []
    for b in load_bindings():
        b_ref = str(b.get("ref") or "")
        if normalize:
            b_ref = full_ref(b_ref)
        if b.get("repo") == repo and b_ref == ref_n:
            hits.append(b)
    return hits


def conflicts() -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for b in load_bindings():
        key = (str(b.get("repo")), full_ref(str(b.get("ref") or "")))
        buckets[key].append(str(b.get("pipeline")))
    return [
        {"repo": k[0], "ref": k[1], "pipelines": sorted(set(v))}
        for k, v in buckets.items()
        if len(set(v)) > 1
    ]


def pipelines_for_repo(repo: str) -> list[str]:
    return sorted({str(b.get("pipeline")) for b in load_bindings() if b.get("repo") == repo})


def coverage_report() -> dict[str, Any]:
    by_repo: dict[str, int] = defaultdict(int)
    for b in load_bindings():
        by_repo[str(b.get("repo"))] += 1
    return {
        "binding_count": len(load_bindings()),
        "by_repo": dict(sorted(by_repo.items())),
        "conflicts": conflicts(),
        "indexed_keys": len(indexed(True)),
    }
