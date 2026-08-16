"""Delivery identity for a pipeline trigger."""

from __future__ import annotations

from cc.util import digest

PREIMAGE_FIELDS = ("repo", "ref", "commit", "pipeline")
SEPARATOR = "|"


def preimage(repo: str, ref: str, commit: str, pipeline: str) -> str:
    """Canonical string that identifies one delivery."""
    return SEPARATOR.join([repo, ref, commit, pipeline])


def event_id(repo: str, ref: str, commit: str, pipeline: str) -> str:
    """Identity of one delivery of one commit to one pipeline.

    Derived only from the delivery coordinates, so the same coordinates always
    produce the same identity and a repeat delivery is recognisable.
    """
    return digest(preimage(repo, ref, commit, pipeline))


def fields(repo: str, ref: str, commit: str, pipeline: str) -> dict[str, str]:
    """Delivery fields in the order the journal records them."""
    return {"repo": repo, "ref": ref, "commit": commit, "pipeline": pipeline}
