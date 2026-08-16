"""Outbox rows held in ``var/outbox.jsonl``."""

from __future__ import annotations

from typing import Any

from cc.home import OUTBOX_KEYS, ensure_layout, outbox_path, webhook_endpoints
from cc.models import WebhookEndpoint
from cc.store.jsonstore import append_row, read_rows, rewrite_rows
from cc.store.lock import guard
from cc.util import ordered_row

STATUS_PENDING = "pending"
STATUS_DELIVERED = "delivered"
STATUS_DEAD = "dead"
FIRST_TICK = 0


def endpoints() -> list[WebhookEndpoint]:
    """Every configured endpoint, enabled or not."""
    return [WebhookEndpoint.from_dict(body) for body in webhook_endpoints()]


def endpoint(name: str) -> WebhookEndpoint | None:
    for entry in endpoints():
        if entry.endpoint == name:
            return entry
    return None


def endpoints_for(pipeline: str) -> list[WebhookEndpoint]:
    """Enabled endpoints that subscribe to this pipeline."""
    return [entry for entry in endpoints() if entry.enabled and entry.wants(pipeline)]


def rows() -> list[dict[str, Any]]:
    """Every outbox row, oldest first."""
    return read_rows(outbox_path())


def next_id() -> int:
    current = rows()
    if not current:
        return 1
    return max(int(row.get("outbox_id") or 0) for row in current) + 1


def find(event: str, endpoint_name: str) -> dict[str, Any] | None:
    """Existing row for one event and endpoint pair."""
    for row in rows():
        if row.get("event_id") == event and row.get("endpoint") == endpoint_name:
            return row
    return None


def for_event(event: str) -> list[dict[str, Any]]:
    """Every row queued for one delivery event."""
    return [row for row in rows() if row.get("event_id") == event]


def _new_row(
    outbox_id: int, event: str, endpoint_name: str, pipeline: str, repo: str, ref: str, commit: str
) -> dict[str, Any]:
    values = {
        "outbox_id": outbox_id,
        "event_id": event,
        "endpoint": endpoint_name,
        "pipeline": pipeline,
        "repo": repo,
        "ref": ref,
        "commit": commit,
        "status": STATUS_PENDING,
        "attempts": 0,
        "next_tick": FIRST_TICK,
    }
    return ordered_row(values, OUTBOX_KEYS)


def enqueue_for_event(
    event: str, pipeline: str, repo: str, ref: str, commit: str
) -> list[dict[str, Any]]:
    """Queue one row per subscribed endpoint for a delivered pipeline event.

    One event and endpoint pair owns at most one row for the lifetime of the
    root, whatever state that row has reached.
    """
    ensure_layout()
    created: list[dict[str, Any]] = []
    with guard("outbox"):
        for entry in endpoints_for(pipeline):
            if find(event, entry.endpoint) is not None:
                continue
            row = _new_row(next_id(), event, entry.endpoint, pipeline, repo, ref, commit)
            append_row(outbox_path(), row)
            created.append(row)
    return created


def replace_row(updated: dict[str, Any]) -> None:
    """Persist an advanced row, keeping journal order stable."""
    current = rows()
    target = int(updated.get("outbox_id") or 0)
    merged = [
        ordered_row(updated, OUTBOX_KEYS) if int(row.get("outbox_id") or 0) == target else row
        for row in current
    ]
    rewrite_rows(outbox_path(), merged)


def summary() -> dict[str, Any]:
    """Counts per status, for operator listings."""
    current = rows()
    return {
        "total": len(current),
        "pending": sum(1 for row in current if row.get("status") == STATUS_PENDING),
        "delivered": sum(1 for row in current if row.get("status") == STATUS_DELIVERED),
        "dead": sum(1 for row in current if row.get("status") == STATUS_DEAD),
    }
