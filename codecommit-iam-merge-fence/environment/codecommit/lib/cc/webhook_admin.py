from __future__ import annotations

from typing import Any

from cc import home
from cc.services.validators import validate_webhook
from cc.util import dump_json, load_json
from cc.webhooks import outbox, retry


def load_webhooks() -> list[dict[str, Any]]:
    return list(load_json(home.webhooks_path(), {"webhooks": []}).get("webhooks") or [])


def save_webhooks(rows: list[dict[str, Any]]) -> None:
    cleaned = [validate_webhook(w) for w in rows]
    dump_json(home.webhooks_path(), {"webhooks": cleaned})


def upsert_webhook(webhook: dict[str, Any]) -> dict[str, Any]:
    webhook = validate_webhook(webhook)
    rows = load_webhooks()
    out: list[dict[str, Any]] = []
    replaced = False
    for row in rows:
        if row.get("id") == webhook["id"]:
            out.append(webhook)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(webhook)
    save_webhooks(out)
    return webhook


def remove_webhook(webhook_id: str) -> bool:
    rows = load_webhooks()
    after = [w for w in rows if w.get("id") != webhook_id]
    save_webhooks(after)
    return len(after) != len(rows)


def outbox_for_webhook(webhook_id: str) -> list[dict[str, Any]]:
    return [r for r in outbox.all_rows() if r.get("webhook_id") == webhook_id]


def requeue_failed(*, fixed: bool = True) -> int:
    rows = outbox.all_rows()
    n = 0
    for row in rows:
        if row.get("status") == "failed" and retry.should_retry(row, fixed=fixed):
            row["status"] = "pending"
            n += 1
    from cc.webhooks.retry import rewrite_outbox

    rewrite_outbox(rows)
    return n


def delivery_stats() -> dict[str, Any]:
    rows = outbox.all_rows()
    by_status: dict[str, int] = {}
    for row in rows:
        st = str(row.get("status"))
        by_status[st] = by_status.get(st, 0) + 1
    return {"total": len(rows), "by_status": by_status, "webhooks": [w.get("id") for w in load_webhooks()]}
