from __future__ import annotations

from pathlib import Path
from typing import Any

from cc.iam import actions as iam_actions
from cc.pipelines.deliver import deliver
from cc.prs import approvals, merge, store as pr_store
from cc.repos import catalog, gitops
from cc.services import authz_gateway, serializers
from cc.util import full_ref
from cc.webhooks.dispatch import dispatch_pending


class ControlPlane:
    """High-level facade used by CLI/API and operator scripts."""

    def __init__(self, *, fixed: bool = False) -> None:
        self.fixed = fixed

    def ensure_repo(self, name: str) -> dict[str, Any]:
        catalog.upsert_repo(name)
        gitops.ensure_bare(name)
        return catalog.require_repo(name)

    def clone(self, principal: str, repo: str, dest: Path, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> None:
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PULL, repo, "main", mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        gitops.clone(repo, dest)

    def push(
        self,
        principal: str,
        repo: str,
        worktree: Path,
        branch: str,
        *,
        mfa: bool = False,
        source_ip: str = "127.0.0.1",
    ) -> dict[str, Any]:
        ref = full_ref(branch)
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PUSH, repo, ref, mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        commit = gitops.push(repo, worktree, branch)
        return serializers.push_success(repo, ref, commit)

    def open_pr(self, principal: str, repo: str, source: str, dest: str, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> dict[str, Any]:
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PULL, repo, source, mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        src = gitops.ref_commit(repo, source)
        pr = pr_store.create(repo, source, dest, src, principal)
        return serializers.pr_success(pr.pr_id, pr.source, pr.dest, pr.source_commit)

    def approve(self, principal: str, pr_id: int) -> dict[str, Any]:
        return approvals.approve(pr_id, principal, fixed=self.fixed)

    def merge(self, principal: str, pr_id: int, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> dict[str, Any]:
        return merge.merge(pr_id, principal, mfa=mfa, source_ip=source_ip, fixed=self.fixed)

    def deliver(self, repo: str, ref: str) -> dict[str, Any]:
        return deliver(repo, ref, fixed=self.fixed)

    def dispatch(self) -> list[dict[str, Any]]:
        sink: list[dict[str, Any]] = []
        return dispatch_pending(fixed=self.fixed, sink=sink)
