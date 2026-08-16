from __future__ import annotations

from typing import Any

from cc import home
from cc.store.jsonstore import JsonStore


def _default() -> dict[str, Any]:
    return {"repos": {}}


def store() -> JsonStore:
    return JsonStore(home.catalog_path(), _default)


def list_repos() -> list[str]:
    data = store().read()
    return sorted((data.get("repos") or {}).keys())


def get_repo(name: str) -> dict[str, Any] | None:
    return (store().read().get("repos") or {}).get(name)


def upsert_repo(name: str, *, default_branch: str = "main", description: str = "") -> dict[str, Any]:
    def mut(data: dict[str, Any]) -> dict[str, Any]:
        repos = data.setdefault("repos", {})
        entry = repos.get(name) or {}
        entry.update(
            {
                "name": name,
                "default_branch": default_branch,
                "description": description,
                "arn": f"arn:local:codecommit:local:000000000000:{name}",
            }
        )
        repos[name] = entry
        return data

    store().update(mut)
    return get_repo(name) or {}


def require_repo(name: str) -> dict[str, Any]:
    entry = get_repo(name)
    if entry is None:
        from cc.errors import ValidationException

        raise ValidationException(code="REPO_NOT_FOUND", repo=name)
    return entry
