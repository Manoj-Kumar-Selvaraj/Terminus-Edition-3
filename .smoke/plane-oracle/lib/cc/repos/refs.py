"""Ref naming rules and ref state lookups for catalogued repositories."""

from __future__ import annotations

from typing import Any

from cc.errors import NotFound, ValidationException
from cc.home import bare_repo_path
from cc.repos import catalog
from cc.repos.gitops import list_refs, ref_commit
from cc.util import normalize_ref, short_ref

BRANCH_NAMESPACE = "refs/heads/"


def full_ref(ref: str) -> str:
    """Normalize a caller ref and reject namespaces the plane does not manage."""
    try:
        value = normalize_ref(ref)
    except ValueError as exc:
        raise ValidationException("BAD_REF", "a ref name is required") from exc
    if not value.startswith(BRANCH_NAMESPACE):
        raise ValidationException(
            "UNSUPPORTED_REF_NAMESPACE", f"only {BRANCH_NAMESPACE}* refs are managed, got {value!r}"
        )
    if value.endswith("/") or ".." in value:
        raise ValidationException("BAD_REF", f"malformed ref {value!r}")
    return value


def branch_of(ref: str) -> str:
    """Branch name for a managed ref."""
    return short_ref(full_ref(ref))


def is_protected(repo: str, ref: str) -> bool:
    """True when the catalog marks this ref as protected."""
    entry = catalog.get(repo)
    return full_ref(ref) in entry.protected_refs


def exists(repo: str, ref: str) -> bool:
    """True when the ref currently resolves in the bare repository."""
    return ref_commit(bare_repo_path(repo), full_ref(ref)) is not None


def tip(repo: str, ref: str) -> str:
    """Object id a managed ref points at."""
    value = full_ref(ref)
    commit = ref_commit(bare_repo_path(repo), value)
    if commit is None:
        raise NotFound("REF_NOT_FOUND", f"{repo} has no ref {value}")
    return commit


def assert_push_allowed(repo: str, ref: str) -> str:
    """A protected ref must already exist before an operator may push to it."""
    value = full_ref(ref)
    if is_protected(repo, value) and not exists(repo, value):
        raise ValidationException(
            "PROTECTED_REF_MISSING",
            f"{value} is protected and must be created by the release process",
        )
    return value


def branches(repo: str) -> dict[str, str]:
    """Branch refs of a repository mapped to object ids."""
    return list_refs(bare_repo_path(repo))


def describe(repo: str) -> dict[str, Any]:
    """Ref state summary used by operator listings."""
    entry = catalog.get(repo)
    refs = branches(repo)
    return {
        "repo": entry.name,
        "default_branch": entry.default_branch,
        "protected_refs": list(entry.protected_refs),
        "branches": dict(sorted(refs.items())),
        "head": refs.get(entry.default_branch),
    }
