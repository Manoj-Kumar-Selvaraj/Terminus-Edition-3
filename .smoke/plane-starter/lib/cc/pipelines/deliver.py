"""Pipeline delivery and the trigger journal in ``var/triggers.jsonl``."""

from __future__ import annotations

from typing import Any

from cc.home import ensure_layout, triggers_path
from cc.iam.actions import START_PIPELINE
from cc.iam.eval import authorize
from cc.pipelines import bindings
from cc.pipelines.event_id import event_id, fields
from cc.repos import catalog, refs
from cc.store.jsonstore import append_row, read_rows
from cc.store.lock import guard
from cc.util import ordered_row
from cc.webhooks import outbox

STATUS_DELIVERED = "delivered"
JOURNAL_KEYS = ["event_id", "repo", "ref", "commit", "status", "pipeline"]


def journal() -> list[dict[str, Any]]:
    """Every journalled trigger row, oldest first."""
    return read_rows(triggers_path())


def journal_ids() -> set[str]:
    """Event ids already present in the journal."""
    return {str(row.get("event_id")) for row in journal()}


def already_journalled(candidate: str) -> bool:
    return candidate in journal_ids()


def _journal_row(candidate: str, repo: str, ref: str, commit: str, pipeline: str) -> dict[str, Any]:
    values: dict[str, Any] = {"event_id": candidate, "status": STATUS_DELIVERED}
    values.update(fields(repo, ref, commit, pipeline))
    return ordered_row(values, JOURNAL_KEYS)


def _record(candidate: str, repo: str, ref: str, commit: str, pipeline: str) -> bool:
    """Append one trigger row; returns True when a new row was written."""
    ensure_layout()
    with guard("triggers"):
        fresh = not already_journalled(candidate)
        append_row(
            triggers_path(),
            _journal_row(candidate, repo, ref, commit, pipeline),
        )
        return fresh


def deliver(
    principal: str,
    repo: str,
    ref: str,
    *,
    mfa: Any = None,
    source_ip: str | None = None,
) -> dict[str, Any]:
    """Start every enabled pipeline bound to this repository and ref."""
    catalog.get(repo)
    target = refs.full_ref(ref)
    authorize(principal, START_PIPELINE, repo, ref=target, mfa=mfa, source_ip=source_ip)
    commit = refs.tip(repo, target)
    matched = bindings.for_ref(repo, ref)
    delivered: list[dict[str, Any]] = []
    for binding in matched:
        candidate = event_id(repo, ref, commit, binding.pipeline)
        fresh = _record(candidate, repo, ref, commit, binding.pipeline)
        outbox.enqueue_for_event(candidate, binding.pipeline, repo, ref, commit)
        delivered.append(
            {
                "pipeline": binding.pipeline,
                "event_id": candidate,
                "duplicate": not fresh,
            }
        )
    return {
        "ok": True,
        "repo": repo,
        "ref": target,
        "commit": commit,
        "duplicate": bool(delivered) and all(entry["duplicate"] for entry in delivered),
        "parked": bindings.parked_for(repo, target),
        "delivered": delivered,
    }
