from __future__ import annotations

from typing import Any

from cc import home
from cc.models import AuditEvent
from cc.util import append_jsonl, read_jsonl


def record(event: AuditEvent, *, fixed: bool = False) -> None:
    if not fixed and not event.allowed:
        return  # Broken: drop denied decisions
    append_jsonl(home.audit_path(), event.to_row())


def record_dict(row: dict[str, Any], *, fixed: bool = False) -> None:
    if not fixed and not row.get("allowed", True):
        return
    append_jsonl(home.audit_path(), row)


def all_events() -> list[dict[str, Any]]:
    return read_jsonl(home.audit_path())
