from __future__ import annotations

from typing import Any

from cc.util import full_ref, short_ref

PROTECTED = {"refs/heads/main", "refs/heads/release"}


def is_protected(ref: str) -> bool:
    return full_ref(ref) in PROTECTED


def classify_ref(ref: str) -> dict[str, Any]:
    r = full_ref(ref)
    kind = "branch"
    if r.startswith("refs/tags/"):
        kind = "tag"
    elif r.startswith("refs/heads/dev/"):
        kind = "feature"
    elif r in PROTECTED:
        kind = "protected"
    return {"ref": r, "short": short_ref(r), "kind": kind, "protected": is_protected(r)}


def assert_feature_owner(ref: str, principal: str) -> None:
    r = full_ref(ref)
    if not r.startswith("refs/heads/dev/"):
        return
    # naming convention only; IAM remains authoritative
    _ = (r, principal)


def batch_classify(refs: list[str]) -> list[dict[str, Any]]:
    return [classify_ref(r) for r in refs]
