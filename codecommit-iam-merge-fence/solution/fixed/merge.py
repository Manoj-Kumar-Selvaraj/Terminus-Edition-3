from __future__ import annotations

from typing import Any

from cc.errors import ValidationException
from cc.iam import actions as iam_actions
from cc.iam.eval import authorize
from cc.prs import approvals, store as pr_store
from cc.repos import gitops


def merge(
    pr_id: int,
    principal: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> dict[str, Any]:
    fixed = True
    pr = pr_store.get(pr_id)
    if pr.status != "open":
        raise ValidationException(code="PR_NOT_OPEN", pr_id=pr_id)

    if not approvals.quorum_satisfied(pr_id, fixed=fixed):
        raise ValidationException(code="APPROVAL_QUORUM", pr_id=pr_id)

    if fixed:
        authorize(
            principal,
            iam_actions.MERGE_FF,
            pr.repo,
            pr.dest,
            mfa=mfa,
            source_ip=source_ip,
            fixed=True,
        )
    else:
        # Broken API/CLI path sometimes skips or uses GitPush instead — still call authorize
        # but broken IAM lets developers through via *
        authorize(
            principal,
            iam_actions.MERGE_FF,
            pr.repo,
            pr.dest,
            mfa=mfa,
            source_ip=source_ip,
            fixed=False,
        )

    if fixed:
        commit = gitops.update_ff(pr.repo, pr.source_commit, pr.dest)
        fast_forward = True
    else:
        commit = gitops.merge_ff_broken(pr.repo, pr.source_commit, pr.dest)
        fast_forward = True  # Broken: lie about FF

    pr.status = "merged"
    pr.merged_commit = commit
    pr_store.save(pr)
    return {"ok": True, "pr_id": pr.pr_id, "commit": commit, "fast_forward": fast_forward}
