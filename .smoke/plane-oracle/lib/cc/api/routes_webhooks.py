"""Webhook routes: read the outbox and drain it at a logical tick."""

from __future__ import annotations

import re
from typing import Any

from cc.api.auth import caller_from
from cc.errors import ValidationException
from cc.webhooks import dispatch as drain


def outbox(
    _match: re.Match[str], query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Outbox rows, optionally narrowed to one delivery event."""
    from cc.api.app import single

    caller = caller_from(headers)
    result = drain.list_outbox(
        caller.principal,
        event=single(query, "event"),
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    return 200, result


def _tick(payload: dict[str, Any]) -> int:
    raw = payload.get("tick")
    if raw is None:
        raise ValidationException("MISSING_FIELD", "body field 'tick' is required")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationException("BAD_TICK", f"tick must be an integer, got {raw!r}") from exc


def dispatch(
    _match: re.Match[str], _query: dict[str, list[str]], headers: Any, body: Any
) -> tuple[int, dict[str, Any]]:
    """Attempt every due outbox row once."""
    from cc.api.app import require_body

    caller = caller_from(headers)
    payload = require_body(body)
    result = drain.dispatch_once(
        caller.principal,
        _tick(payload),
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    return 200, result
