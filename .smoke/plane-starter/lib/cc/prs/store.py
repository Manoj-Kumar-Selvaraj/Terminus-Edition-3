"""Pull-request records held in ``var/prs.json``."""

from __future__ import annotations

from typing import Any

from cc.errors import NotFound, ValidationException
from cc.home import bare_repo_path, ensure_layout, prs_path
from cc.models import PullRequest
from cc.repos import refs
from cc.repos.gitops import commit_subject
from cc.store.jsonstore import load_document, save_document
from cc.store.lock import guard
from cc.util import stamp

EMPTY: dict[str, Any] = {"next_id": 1, "items": {}}


def load() -> dict[str, Any]:
    """Whole store document, with defaults filled in."""
    body = load_document(prs_path(), None)
    if not isinstance(body, dict):
        return {"next_id": 1, "items": {}}
    items = body.get("items")
    return {
        "next_id": int(body.get("next_id") or 1),
        "items": items if isinstance(items, dict) else {},
    }


def save(document: dict[str, Any]) -> None:
    ensure_layout()
    save_document(prs_path(), document)


def initialize() -> None:
    """Create an empty store when a root is first bootstrapped."""
    if not prs_path().is_file():
        save(dict(EMPTY))


def all_requests() -> list[PullRequest]:
    """Every stored pull request, ordered by id."""
    document = load()
    requests = [PullRequest.from_dict(body) for body in document["items"].values()]
    return sorted(requests, key=lambda item: item.pr_id)


def for_repo(repo: str) -> list[PullRequest]:
    return [item for item in all_requests() if item.repo == repo]


def get(pr_id: int) -> PullRequest:
    """One stored pull request."""
    document = load()
    body = document["items"].get(str(pr_id))
    if body is None:
        raise NotFound("PR_NOT_FOUND", f"no pull request {pr_id}")
    return PullRequest.from_dict(body)


def require_open(pr_id: int) -> PullRequest:
    """One stored pull request that has not been landed or closed yet."""
    request = get(pr_id)
    if not request.is_open:
        raise ValidationException(
            "PR_NOT_OPEN", f"pull request {pr_id} is {request.status}", status=request.status
        )
    return request


def _write(request: PullRequest) -> PullRequest:
    document = load()
    document["items"][str(request.pr_id)] = request.as_dict()
    save(document)
    return request


def create(repo: str, source: str, dest: str, author: str) -> PullRequest:
    """Open a pull request between two existing refs of one repository."""
    source_ref = refs.full_ref(source)
    dest_ref = refs.full_ref(dest)
    if source_ref == dest_ref:
        raise ValidationException("SAME_REF", "source and destination refs are identical")
    source_commit = refs.tip(repo, source_ref)
    base_commit = refs.tip(repo, dest_ref)
    subject = commit_subject(bare_repo_path(repo), source_commit)
    with guard("prs"):
        document = load()
        pr_id = int(document["next_id"])
        request = PullRequest(
            pr_id=pr_id,
            repo=repo,
            source=source_ref,
            dest=dest_ref,
            author=author,
            source_commit=source_commit,
            base_commit=base_commit,
            status="open",
            approvals=[],
            created_at=stamp(),
            title=subject,
        )
        document["items"][str(pr_id)] = request.as_dict()
        document["next_id"] = pr_id + 1
        save(document)
    return request


def add_approval(pr_id: int, approver: str) -> PullRequest:
    """Record an approval stamp against an open pull request."""
    with guard("prs"):
        request = require_open(pr_id)
        request.approvals.append(approver)
        return _write(request)


def mark_merged(pr_id: int, commit: str, merged_by: str) -> PullRequest:
    """Persist the landed state of a pull request."""
    with guard("prs"):
        request = require_open(pr_id)
        request.status = "merged"
        request.merged_commit = commit
        request.merged_by = merged_by
        return _write(request)
