from __future__ import annotations

from typing import Any

from cc import home
from cc.models import PullRequest
from cc.store.jsonstore import JsonStore
from cc.util import full_ref


def _default() -> dict[str, Any]:
    return {"next_id": 1, "items": {}}


def store() -> JsonStore:
    return JsonStore(home.prs_path(), _default)


def create(repo: str, source: str, dest: str, source_commit: str, author: str) -> PullRequest:
    def mut(data: dict[str, Any]) -> dict[str, Any]:
        pr_id = int(data.get("next_id") or 1)
        data["next_id"] = pr_id + 1
        item = PullRequest(
            pr_id=pr_id,
            repo=repo,
            source=full_ref(source),
            dest=full_ref(dest),
            source_commit=source_commit,
            author=author,
            status="open",
            approvals=[],
        )
        data.setdefault("items", {})[str(pr_id)] = item.to_dict()
        return data

    data = store().update(mut)
    pr_id = int(data["next_id"]) - 1
    return get(pr_id)


def get(pr_id: int) -> PullRequest:
    raw = (store().read().get("items") or {}).get(str(pr_id))
    if raw is None:
        from cc.errors import ValidationException

        raise ValidationException(code="PR_NOT_FOUND", pr_id=pr_id)
    return PullRequest(**raw)


def save(pr: PullRequest) -> PullRequest:
    def mut(data: dict[str, Any]) -> dict[str, Any]:
        data.setdefault("items", {})[str(pr.pr_id)] = pr.to_dict()
        return data

    store().update(mut)
    return pr


def list_open(repo: str | None = None) -> list[PullRequest]:
    items = store().read().get("items") or {}
    out: list[PullRequest] = []
    for raw in items.values():
        pr = PullRequest(**raw)
        if pr.status != "open":
            continue
        if repo and pr.repo != repo:
            continue
        out.append(pr)
    return sorted(out, key=lambda p: p.pr_id)
