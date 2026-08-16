"""The merge fence.

A pull request lands only when the caller is authorized for the destination,
the destination's approval rule is satisfied, and the destination can move
forward without a merge commit.
"""

from __future__ import annotations

from typing import Any

from cc.errors import NotFound
from cc.home import bare_repo_path
from cc.iam.actions import MERGE_BY_FAST_FORWARD
from cc.iam.eval import authorize
from cc.models import PullRequest
from cc.prs import approvals, store
from cc.repos import catalog
from cc.repos.gitops import commit_parents, merge_ff, ref_commit


def preview(repo: str, pr_id: int) -> dict[str, Any]:
    """Report what a merge would do without changing any ref."""
    request = store.get(pr_id)
    bare = bare_repo_path(repo)
    dest_tip = ref_commit(bare, request.dest)
    return {
        "pr_id": request.pr_id,
        "repo": request.repo,
        "dest": request.dest,
        "dest_commit": dest_tip,
        "source_commit": request.source_commit,
        "status": request.status,
        "quorum": approvals.status(request),
    }


def _resolve(repo: str, pr_id: int) -> PullRequest:
    catalog.get(repo)
    request = store.require_open(pr_id)
    if request.repo != repo:
        raise NotFound("PR_NOT_FOUND", f"pull request {pr_id} does not belong to {repo}")
    return request


def merge_pull_request(
    principal: str,
    repo: str,
    pr_id: int,
    *,
    mfa: Any = None,
    source_ip: str | None = None,
) -> dict[str, Any]:
    """Land one pull request by fast-forward."""
    request = _resolve(repo, pr_id)
    authorize(
        principal,
        MERGE_BY_FAST_FORWARD,
        repo,
        ref=request.dest,
        mfa=mfa,
        source_ip=source_ip,
    )
    quorum = approvals.assert_quorum(request)
    bare = bare_repo_path(repo)
    landed = merge_ff(bare, request.dest, request.source_commit)
    store.mark_merged(pr_id, landed, principal)
    return {
        "ok": True,
        "pr_id": request.pr_id,
        "repo": repo,
        "dest": request.dest,
        "source": request.source,
        "commit": landed,
        "fast_forward": True,
        "parents": commit_parents(bare, landed),
        "approvals": quorum["counted"],
        "rule_id": quorum["rule_id"],
    }
