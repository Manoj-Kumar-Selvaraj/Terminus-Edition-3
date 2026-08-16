"""Outbox drain.

The lab transport is a file sink: a successful attempt appends one line to the
endpoint's sink file. ``reject_until_attempt`` reproduces an endpoint that turns
away the first attempts, which is how retry behaviour is exercised without
reaching the network.
"""

from __future__ import annotations

from typing import Any

from cc.errors import ValidationException
from cc.home import ensure_layout, resolve_sink
from cc.iam.actions import DISPATCH_OUTBOX, LIST_OUTBOX
from cc.iam.eval import authorize
from cc.models import WebhookEndpoint
from cc.store.jsonstore import append_row
from cc.webhooks import outbox, retry
from cc.webhooks.outbox import STATUS_DEAD, STATUS_DELIVERED, STATUS_PENDING


def _selectable(row: dict[str, Any]) -> bool:
    """True when a row is still a candidate for an attempt."""
    return str(row.get("status")) != STATUS_DELIVERED


def transport_send(endpoint: WebhookEndpoint, row: dict[str, Any], attempt_no: int) -> bool:
    """Attempt one delivery through the lab file-sink transport."""
    if attempt_no <= endpoint.reject_until_attempt:
        return False
    sink = resolve_sink(endpoint.sink)
    sink.parent.mkdir(parents=True, exist_ok=True)
    append_row(
        sink,
        {
            "event_id": row.get("event_id"),
            "endpoint": endpoint.endpoint,
            "url": endpoint.url,
            "pipeline": row.get("pipeline"),
            "repo": row.get("repo"),
            "ref": row.get("ref"),
            "commit": row.get("commit"),
            "attempt": attempt_no,
        },
    )
    return True


def dead_rows() -> list[int]:
    """Outbox ids that exhausted their endpoint's attempt budget."""
    return [
        int(row["outbox_id"]) for row in outbox.rows() if row.get("status") == STATUS_DEAD
    ]


def _endpoint_for(row: dict[str, Any]) -> WebhookEndpoint:
    name = str(row.get("endpoint"))
    entry = outbox.endpoint(name)
    if entry is None:
        raise ValidationException("UNKNOWN_ENDPOINT", f"row references endpoint {name!r}")
    return entry


def dispatch_once(
    principal: str,
    tick: int,
    *,
    mfa: Any = None,
    source_ip: str | None = None,
) -> dict[str, Any]:
    """Attempt every due outbox row once at this logical tick."""
    if tick < 0:
        raise ValidationException("BAD_TICK", "tick must not be negative")
    authorize(principal, DISPATCH_OUTBOX, "*", mfa=mfa, source_ip=source_ip)
    ensure_layout()
    delivered: list[int] = []
    retried: list[int] = []
    dead: list[int] = []
    candidates = [row for row in outbox.rows() if _selectable(row)]
    for row in sorted(retry.due(candidates, tick), key=lambda item: int(item["outbox_id"])):
        entry = _endpoint_for(row)
        attempts = int(row.get("attempts") or 0) + 1
        outbox_id = int(row["outbox_id"])
        updated = dict(row)
        updated["attempts"] = attempts
        if transport_send(entry, row, attempts):
            updated["status"] = STATUS_DELIVERED
            updated["next_tick"] = tick
            delivered.append(outbox_id)
        else:
            updated["status"] = STATUS_PENDING
            updated["next_tick"] = tick + retry.backoff_delay(entry, attempts)
            retried.append(outbox_id)
        outbox.replace_row(updated)
    return {
        "ok": True,
        "tick": tick,
        "attempted": len(delivered) + len(retried) + len(dead),
        "delivered": delivered,
        "retried": retried,
        "dead": dead,
        "summary": outbox.summary(),
    }


def list_outbox(
    principal: str,
    *,
    event: str | None = None,
    mfa: Any = None,
    source_ip: str | None = None,
) -> dict[str, Any]:
    """Read the outbox, optionally narrowed to one delivery event."""
    authorize(principal, LIST_OUTBOX, "*", mfa=mfa, source_ip=source_ip)
    rows = outbox.for_event(event) if event else outbox.rows()
    return {
        "ok": True,
        "count": len(rows),
        "summary": outbox.summary(),
        "dead": dead_rows(),
        "rows": rows,
    }
