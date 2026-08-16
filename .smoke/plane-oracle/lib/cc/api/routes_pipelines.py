"""Pipeline routes: delivery and the trigger journal."""

from __future__ import annotations

import re
from typing import Any

from cc.api.auth import caller_from
from cc.pipelines import bindings, deliver as delivery
from cc.repos import catalog


def deliver(
    _match: re.Match[str], _query: dict[str, list[str]], headers: Any, body: Any
) -> tuple[int, dict[str, Any]]:
    """Start every enabled pipeline bound to a repository ref."""
    from cc.api.app import field, require_body

    caller = caller_from(headers)
    payload = require_body(body)
    repo = field(payload, "repo")
    ref = field(payload, "ref")
    result = delivery.deliver(
        caller.principal,
        repo,
        ref,
        mfa=caller.mfa,
        source_ip=caller.source_ip,
    )
    return 200, result


def journal(
    _match: re.Match[str], query: dict[str, list[str]], headers: Any, _body: Any
) -> tuple[int, dict[str, Any]]:
    """Read the trigger journal, optionally narrowed to one repository."""
    from cc.api.app import single

    caller_from(headers)
    repo = single(query, "repo")
    rows = delivery.journal()
    if repo:
        catalog.get(repo)
        rows = [row for row in rows if row.get("repo") == repo]
    return 200, {
        "ok": True,
        "count": len(rows),
        "rows": rows,
        "bindings": bindings.describe(repo)["bindings"] if repo else [],
    }
