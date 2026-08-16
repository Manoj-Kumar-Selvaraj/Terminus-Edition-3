from __future__ import annotations

from typing import Any

from cc import home
from cc.models import OutboxItem
from cc.util import append_jsonl, load_json, read_jsonl


def load_webhook_config() -> list[dict[str, Any]]:
    data = load_json(home.webhooks_path(), {"webhooks": []})
    return list(data.get("webhooks") or [])


def enqueue_for_delivery(delivery_row: dict[str, Any]) -> list[OutboxItem]:
    items: list[OutboxItem] = []
    for wh in load_webhook_config():
        if wh.get("pipeline") and wh.get("pipeline") != delivery_row.get("pipeline"):
            continue
        item = OutboxItem(
            event_id=str(delivery_row["event_id"]),
            repo=str(delivery_row["repo"]),
            ref=str(delivery_row["ref"]),
            commit=str(delivery_row["commit"]),
            pipeline=str(delivery_row["pipeline"]),
            webhook_id=str(wh.get("id")),
            status="pending",
            attempts=0,
        )
        append_jsonl(home.outbox_path(), item.to_row())
        items.append(item)
    return items


def pending() -> list[dict[str, Any]]:
    return [r for r in read_jsonl(home.outbox_path()) if r.get("status") in ("pending", "failed")]


def all_rows() -> list[dict[str, Any]]:
    return read_jsonl(home.outbox_path())
