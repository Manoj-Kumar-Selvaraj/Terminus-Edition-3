"""Webhook payload signing for durable outbox rows."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from cc import home
from cc.util import load_json


def webhook_secret(webhook_id: str, default: str = "settle") -> str:
    data = load_json(home.webhooks_path(), {"webhooks": []})
    for row in data.get("webhooks") or []:
        if str(row.get("id")) == webhook_id:
            return str(row.get("secret") or default)
    return default


def sign_delivery(event_id: str, pipeline: str, commit: str, secret: str) -> str:
    preimage = f"{event_id}|{pipeline}|{commit}".encode()
    return hmac.new(secret.encode(), preimage, hashlib.sha256).hexdigest()


def verify_signature(row: dict[str, Any], *, secret: str | None = None) -> bool:
    webhook_id = str(row.get("webhook_id") or "")
    sec = secret if secret is not None else webhook_secret(webhook_id)
    expected = sign_delivery(
        str(row.get("event_id") or ""),
        str(row.get("pipeline") or ""),
        str(row.get("commit") or ""),
        sec,
    )
    actual = str(row.get("signature") or "")
    return hmac.compare_digest(expected, actual)


def attach_signature(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    wid = str(out.get("webhook_id") or "")
    out["signature"] = sign_delivery(
        str(out.get("event_id") or ""),
        str(out.get("pipeline") or ""),
        str(out.get("commit") or ""),
        webhook_secret(wid),
    )
    return out


def payload_for_dispatch(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": row.get("event_id"),
        "repo": row.get("repo"),
        "ref": row.get("ref"),
        "commit": row.get("commit"),
        "pipeline": row.get("pipeline"),
        "webhook_id": row.get("webhook_id"),
        "signature": row.get("signature"),
    }
