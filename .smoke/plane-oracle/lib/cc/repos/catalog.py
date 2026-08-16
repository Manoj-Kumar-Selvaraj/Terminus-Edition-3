"""Repository catalog held in ``var/catalog.json``."""

from __future__ import annotations

from typing import Any

from cc.errors import NotFound, ValidationException
from cc.home import catalog_path, ensure_layout, repo_arn
from cc.iam.actions import GET_REPOSITORY
from cc.models import Repository
from cc.store.jsonstore import load_document, save_document
from cc.store.lock import guard

EMPTY: dict[str, Any] = {"repos": []}


def load() -> list[Repository]:
    """Every catalogued repository, in registration order."""
    body = load_document(catalog_path(), EMPTY)
    entries = body.get("repos") if isinstance(body, dict) else None
    if not isinstance(entries, list):
        return []
    return [Repository.from_dict(entry) for entry in entries]


def save(repos: list[Repository]) -> None:
    """Replace the catalog document."""
    ensure_layout()
    save_document(catalog_path(), {"repos": [repo.as_dict() for repo in repos]})


def names() -> list[str]:
    return [repo.name for repo in load()]


def exists(name: str) -> bool:
    return any(repo.name == name for repo in load())


def get(name: str) -> Repository:
    """Catalog entry for a repository, or a control-plane not-found error."""
    for repo in load():
        if repo.name == name:
            return repo
    raise NotFound("REPO_NOT_FOUND", f"no repository named {name!r}")


def register(
    name: str,
    default_branch: str = "refs/heads/main",
    protected_refs: tuple[str, ...] = (),
    description: str = "",
) -> Repository:
    """Add a repository to the catalog, or return the existing entry."""
    if not name or "/" in name or name.endswith(".git"):
        raise ValidationException("BAD_REPO_NAME", f"invalid repository name {name!r}")
    with guard("catalog"):
        current = load()
        for repo in current:
            if repo.name == name:
                return repo
        entry = Repository(
            name=name,
            arn=repo_arn(name),
            default_branch=default_branch,
            protected_refs=protected_refs,
            description=description,
        )
        current.append(entry)
        save(current)
        return entry


def visible_to(principal: str, source_ip: str | None = None) -> list[dict[str, Any]]:
    """Catalog entries whose metadata the caller is allowed to read."""
    from cc.iam.eval import probe

    visible: list[dict[str, Any]] = []
    for repo in load():
        decision = probe(principal, GET_REPOSITORY, repo.name, source_ip=source_ip)
        if decision.allowed:
            visible.append(repo.as_dict())
    return visible
