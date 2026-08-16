from __future__ import annotations

from cc.repos import gitops
from cc.util import full_ref


def resolve_default_branch(name: str) -> str:
    from cc.repos.catalog import get_repo

    entry = get_repo(name) or {}
    return full_ref(str(entry.get("default_branch") or "main"))


def normalize_ref(ref: str) -> str:
    return full_ref(ref)


def tip(name: str, ref: str) -> str:
    return gitops.ref_commit(name, normalize_ref(ref))
