"""Filtered reads over the recorded decision log."""

from __future__ import annotations

from typing import Any

from cc.audit.log import history
from cc.errors import ValidationException

FILTER_FIELDS = ("principal", "action", "repo", "decision")
DECISIONS = frozenset({"allow", "deny"})


def build_filters(
    principal: str | None = None,
    action: str | None = None,
    repo: str | None = None,
    decision: str | None = None,
) -> dict[str, str]:
    """Collect the supplied filters, rejecting values the log cannot hold."""
    filters: dict[str, str] = {}
    if principal:
        filters["principal"] = principal
    if action:
        filters["action"] = action
    if repo:
        filters["repo"] = repo
    if decision:
        if decision not in DECISIONS:
            raise ValidationException(
                "BAD_DECISION_FILTER", f"decision must be allow or deny, got {decision!r}"
            )
        filters["decision"] = decision
    return filters


def row_matches(row: dict[str, Any], filters: dict[str, str]) -> bool:
    """Test one row against the requested filters."""
    if not filters:
        return True
    hits = [row.get(field) == value for field, value in filters.items()]
    return any(hits)


def select(rows: list[dict[str, Any]], filters: dict[str, str], limit: int = 0) -> list[dict[str, Any]]:
    """Apply the filters in log order and cap the result when a limit is set."""
    matched = [row for row in rows if row_matches(row, filters)]
    if limit and limit > 0:
        return matched[:limit]
    return matched


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts that make a filtered read easy to eyeball."""
    allowed = sum(1 for row in rows if row.get("decision") == "allow")
    denied = sum(1 for row in rows if row.get("decision") == "deny")
    principals = sorted({str(row.get("principal")) for row in rows if row.get("principal")})
    return {"allow": allowed, "deny": denied, "principals": principals}


def query(
    principal: str | None = None,
    action: str | None = None,
    repo: str | None = None,
    decision: str | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    """Read the decision log with AND-combined filters."""
    filters = build_filters(principal, action, repo, decision)
    rows = select(history(), filters, limit)
    return {
        "ok": True,
        "count": len(rows),
        "filters": dict(sorted(filters.items())),
        "summary": summarize(rows),
        "rows": rows,
    }
