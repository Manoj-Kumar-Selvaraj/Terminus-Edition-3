"""Decision recorder.

Both operator surfaces funnel through :func:`record_decision`, so the log is a
complete history of what the evaluator decided and why.
"""

from __future__ import annotations

from typing import Any

from cc.home import AUDIT_KEYS, audit_path, ensure_layout
from cc.models import Decision, RequestContext
from cc.store.jsonstore import append_row, read_rows, row_count
from cc.store.lock import guard
from cc.util import ordered_row

ALLOW = "allow"
DENY = "deny"


def next_seq() -> int:
    """Sequence number for the next decision row."""
    return row_count(audit_path()) + 1


def _allow_row(seq: int, request: RequestContext, decision: Decision) -> dict[str, Any]:
    values = {
        "seq": seq,
        "principal": request.principal,
        "action": request.action,
        "repo": request.repo,
        "ref": request.ref,
        "decision": ALLOW,
        "reason": decision.reason,
        "source_ip": request.source_ip,
        "mfa": bool(request.mfa),
    }
    return ordered_row(values, AUDIT_KEYS)


def _deny_row(seq: int, request: RequestContext, decision: Decision) -> dict[str, Any]:
    values = {
        "seq": seq,
        "principal": request.principal,
        "repo": request.repo,
        "ref": request.ref,
        "decision": DENY,
        "reason": decision.reason,
        "source_ip": request.source_ip,
        "mfa": bool(request.mfa),
    }
    return ordered_row(values, [key for key in AUDIT_KEYS if key in values])


def build_row(seq: int, request: RequestContext, decision: Decision) -> dict[str, Any]:
    """Render one decision row in the contracted key order."""
    if decision.allowed:
        return _allow_row(seq, request, decision)
    return _deny_row(seq, request, decision)


def record_decision(request: RequestContext, decision: Decision) -> dict[str, Any]:
    """Append one decision row and return what was written."""
    ensure_layout()
    with guard("audit"):
        row = build_row(next_seq(), request, decision)
        append_row(audit_path(), row)
    return row


def history() -> list[dict[str, Any]]:
    """Every recorded decision row, oldest first."""
    return read_rows(audit_path())


def last_row() -> dict[str, Any] | None:
    """Most recent decision row, or None when nothing has been recorded."""
    rows = history()
    return rows[-1] if rows else None
