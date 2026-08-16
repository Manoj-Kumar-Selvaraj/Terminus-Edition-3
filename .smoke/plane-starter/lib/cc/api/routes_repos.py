"""Repository routes: catalog listing, ref state, and ref updates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from cc.api.auth import caller_from
from cc.home import bare_repo_path
from cc.iam.actions import GET_REPOSITORY, GIT_PUSH
from cc.iam.eval import authorize
from cc.repos import catalog, refs
from cc.repos.gitops import push_head


def list_repos(
    _match: re.Match[str], _query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Repositories whose metadata the caller may read."""
    caller = caller_from(headers)
    visible = catalog.visible_to(caller.principal, caller.source_ip)
    return 200, {"ok": True, "count": len(visible), "repos": visible}


def list_refs(
    match: re.Match[str], _query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Branch state of one repository."""
    caller = caller_from(headers)
    repo = match.group("repo")
    catalog.get(repo)
    authorize(
        caller.principal,
        GET_REPOSITORY,
        repo,
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    return 200, {"ok": True, **refs.describe(repo)}


def push(
    match: re.Match[str], _query: dict[str, list[str]], headers: Any, body: Any
) -> tuple[int, dict[str, Any]]:
    """Update one branch of a repository from a local working tree."""
    from cc.api.app import field, require_body

    caller = caller_from(headers)
    payload = require_body(body)
    repo = match.group("repo")
    catalog.get(repo)
    worktree = Path(field(payload, "worktree"))
    target = refs.full_ref(field(payload, "branch"))
    authorize(
        caller.principal,
        GIT_PUSH,
        repo,
        ref=target,
        mfa=True,
        source_ip=caller.source_ip,
    )
    refs.assert_push_allowed(repo, target)
    commit = push_head(worktree, bare_repo_path(repo), target)
    return 200, {"ok": True, "repo": repo, "ref": target, "commit": commit}
