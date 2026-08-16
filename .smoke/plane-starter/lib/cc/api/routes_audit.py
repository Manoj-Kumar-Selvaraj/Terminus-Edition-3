"""Audit route: filtered reads over recorded authorization decisions."""

from __future__ import annotations

import re
from typing import Any

from cc.api.auth import caller_from
from cc.audit import query as audit_query
from cc.errors import ValidationException
from cc.iam.actions import QUERY_AUTHZ_LOG
from cc.iam.eval import authorize


def _limit(raw: str | None) -> int:
    if raw is None:
        return 0
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationException("BAD_LIMIT", f"limit must be an integer, got {raw!r}") from exc
    if value < 0:
        raise ValidationException("BAD_LIMIT", "limit must not be negative")
    return value


def query(
    _match: re.Match[str], params: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Read the decision log with AND-combined filters."""
    from cc.api.app import single

    caller = caller_from(headers)
    authorize(
        caller.principal,
        QUERY_AUTHZ_LOG,
        "*",
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    result = audit_query.query(
        principal=single(params, "principal"),
        action=single(params, "action"),
        repo=single(params, "repo"),
        decision=single(params, "decision"),
        limit=_limit(single(params, "limit")),
    )
    return 200, result
