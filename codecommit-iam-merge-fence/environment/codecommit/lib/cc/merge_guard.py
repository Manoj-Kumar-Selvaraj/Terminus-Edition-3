"""Merge-path guards: linear history, ancestor checks, lease coupling."""

from __future__ import annotations

from typing import Any

from cc import branch_protection, ref_lease
from cc.errors import ValidationException
from cc.repos import gitops
from cc.util import full_ref


def ensure_fast_forward(repo: str, source_commit: str, dest_ref: str) -> None:
    dest = full_ref(dest_ref)
    tip = gitops.ref_commit(repo, dest)
    if tip == source_commit:
        return
    if not gitops.is_ancestor(repo, tip, source_commit):
        raise ValidationException(code="NOT_FAST_FORWARD", repo=repo, dest=dest)


def parents_of(repo: str, rev: str) -> list[str]:
    return gitops.parents(repo, rev)


def assert_single_parent_tip(repo: str, rev: str) -> None:
    parents = parents_of(repo, rev)
    if len(parents) > 1:
        raise ValidationException(code="NON_LINEAR_HISTORY", repo=repo, rev=rev)


def prepare_protected_merge(
    repo: str,
    dest_ref: str,
    principal: str,
    source_commit: str,
    *,
    fixed: bool,
) -> dict[str, Any]:
    meta = branch_protection.assert_merge_allowed(repo, dest_ref, principal=principal)
    lease = None
    if meta.get("require_lease") and fixed:
        lease = ref_lease.acquire(repo, dest_ref, principal)
    if meta.get("require_linear_history") and fixed:
        ensure_fast_forward(repo, source_commit, dest_ref)
    return {"protection": meta, "lease": lease}


def finish_protected_merge(lease: dict[str, Any] | None) -> None:
    if not lease:
        return
    ref_lease.release(str(lease["repo"]), str(lease["ref"]), str(lease["token"]))


def describe_merge_readiness(
    repo: str, dest_ref: str, source_commit: str, principal: str
) -> dict[str, Any]:
    rules = branch_protection.matching_rules(repo, dest_ref)
    tip = gitops.ref_commit(repo, dest_ref)
    ancestor = gitops.is_ancestor(repo, tip, source_commit) if tip else False
    return {
        "repo": repo,
        "dest": full_ref(dest_ref),
        "tip": tip,
        "source_commit": source_commit,
        "is_ancestor": ancestor,
        "protection_rules": len(rules),
        "active_leases": ref_lease.active_leases(),
        "principal": principal,
    }
