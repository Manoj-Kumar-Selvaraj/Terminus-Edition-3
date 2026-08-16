"""Retry accounting for outbox rows.

Ticks are a logical clock supplied by the operator draining the outbox, so the
same sequence of dispatch calls always produces the same row history.
"""

from __future__ import annotations

from typing import Any

from cc.models import WebhookEndpoint
from cc.webhooks.outbox import STATUS_DEAD, STATUS_PENDING


def backoff_delay(endpoint: WebhookEndpoint, attempts: int) -> int:
    """Ticks to wait before the next attempt of a row that just failed.

    The wait doubles per recorded attempt from the endpoint's base delay.
    """
    base = max(1, endpoint.backoff_base_ticks)
    exponent = max(0, attempts - 1)
    return base * (2**exponent)


def is_exhausted(endpoint: WebhookEndpoint, attempts: int) -> bool:
    """True when a row has used up the endpoint's attempt budget."""
    return attempts >= max(1, endpoint.max_attempts)


def remaining_attempts(endpoint: WebhookEndpoint, attempts: int) -> int:
    """Attempts still available to a row."""
    return max(0, max(1, endpoint.max_attempts) - attempts)


def plan_after_failure(endpoint: WebhookEndpoint, attempts: int, tick: int) -> dict[str, Any]:
    """State a row moves to after a failed attempt."""
    if is_exhausted(endpoint, attempts):
        return {"status": STATUS_DEAD, "attempts": attempts, "next_tick": tick}
    return {
        "status": STATUS_PENDING,
        "attempts": attempts,
        "next_tick": tick + backoff_delay(endpoint, attempts),
    }


def due(rows: list[dict[str, Any]], tick: int) -> list[dict[str, Any]]:
    """Rows whose next attempt is scheduled at or before this tick."""
    return [row for row in rows if int(row.get("next_tick") or 0) <= tick]


def describe(endpoint: WebhookEndpoint, row: dict[str, Any]) -> dict[str, Any]:
    """Retry state of one row against its endpoint budget."""
    attempts = int(row.get("attempts") or 0)
    return {
        "outbox_id": row.get("outbox_id"),
        "endpoint": endpoint.endpoint,
        "attempts": attempts,
        "max_attempts": endpoint.max_attempts,
        "remaining": remaining_attempts(endpoint, attempts),
        "next_tick": int(row.get("next_tick") or 0),
    }
