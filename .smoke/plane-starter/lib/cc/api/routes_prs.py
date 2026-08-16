"""Pull-request routes: open, read, stamp, and land."""

from __future__ import annotations

import re
from typing import Any

from cc.api.auth import caller_from
from cc.home import bare_repo_path
from cc.iam.actions import CREATE_PULL_REQUEST, UPDATE_APPROVAL_STATE
from cc.iam.eval import authorize
from cc.prs import approvals, store
from cc.repos import catalog
from cc.repos.gitops import commit_parents, merge_ff


def list_prs(
    _match: re.Match[str], query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Stored pull requests, optionally narrowed to one repository."""
    from cc.api.app import single

    caller_from(headers)
    repo = single(query, "repo")
    requests = store.for_repo(repo) if repo else store.all_requests()
    return 200, {
        "ok": True,
        "count": len(requests),
        "prs": [item.as_dict() for item in requests],
    }


def get_pr(
    match: re.Match[str], _query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """One stored pull request with its quorum state."""
    caller_from(headers)
    request = store.get(int(match.group("pr_id")))
    return 200, {"ok": True, "pr": request.as_dict(), "quorum": approvals.status(request)}


def create_pr(
    _match: re.Match[str], _query: dict[str, list[str]], headers: Any, body: Any
) -> tuple[int, dict[str, Any]]:
    """Open a pull request between two refs of one repository."""
    from cc.api.app import field, require_body

    caller = caller_from(headers)
    payload = require_body(body)
    repo = field(payload, "repo")
    catalog.get(repo)
    source = field(payload, "source")
    dest = field(payload, "dest")
    authorize(
        caller.principal,
        CREATE_PULL_REQUEST,
        repo,
        ref=dest,
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    request = store.create(repo, source, dest, caller.principal)
    return 200, {"ok": True, "pr_id": request.pr_id, "pr": request.as_dict()}


def approve_pr(
    match: re.Match[str], _query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Stamp one open pull request."""
    caller = caller_from(headers)
    pr_id = int(match.group("pr_id"))
    request = store.require_open(pr_id)
    authorize(
        caller.principal,
        UPDATE_APPROVAL_STATE,
        request.repo,
        ref=request.dest,
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    updated = store.add_approval(pr_id, caller.principal)
    return 200, {
        "ok": True,
        "pr_id": pr_id,
        "approvals": sorted(updated.approvals),
        "quorum": approvals.status(updated),
    }


def merge_pr(
    match: re.Match[str], _query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Land one pull request onto its destination ref."""
    caller = caller_from(headers)
    pr_id = int(match.group("pr_id"))
    request = store.require_open(pr_id)
    quorum = approvals.assert_quorum(request)
    bare = bare_repo_path(request.repo)
    landed = merge_ff(bare, request.dest, request.source_commit)
    store.mark_merged(pr_id, landed, caller.principal)
    return 200, {
        "ok": True,
        "pr_id": pr_id,
        "repo": request.repo,
        "dest": request.dest,
        "source": request.source,
        "commit": landed,
        "fast_forward": True,
        "parents": commit_parents(bare, landed),
        "approvals": quorum["counted"],
        "rule_id": quorum["rule_id"],
    }
