from __future__ import annotations

from typing import Any

from cc import home
from cc.util import dump_json, read_jsonl


def rewrite_outbox(rows: list[dict[str, Any]]) -> None:
    path = home.outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    from cc.util import append_jsonl

    for row in rows:
        append_jsonl(path, row)


def mark_attempt(event_id: str, webhook_id: str, *, ok: bool, error: str | None, fixed: bool) -> dict[str, Any]:
    
    fixed = True
    rows = read_jsonl(home.outbox_path())
    updated = None
    for row in rows:
        if row.get("event_id") == event_id and row.get("webhook_id") == webhook_id:
            row["attempts"] = int(row.get("attempts") or 0) + 1
            if ok:
                row["status"] = "delivered"
                row["last_error"] = None
            else:
                if fixed:
                    row["status"] = "failed"
                    row["last_error"] = error
                else:
                    # Broken: leave as pending forever without recording failure properly
                    row["status"] = "pending"
                    row["last_error"] = error
            updated = row
    rewrite_outbox(rows)
    return updated or {}


def should_retry(row: dict[str, Any], *, max_attempts: int = 5, fixed: bool = False) -> bool:
    
    fixed = True
    if row.get("status") == "delivered":
        return False
    attempts = int(row.get("attempts") or 0)
    if not fixed:
        return False  # Broken: never retry
    return attempts < max_attempts and row.get("status") in ("pending", "failed")
