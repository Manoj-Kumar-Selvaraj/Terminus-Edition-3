from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from checkout.models import Order
from controlplane.idempotency import claim_side_effect
from fulfill.capture_pipeline import (
    decide_claim,
    delivery_attempt_record,
    payload_hash_for,
    should_emit_webhook,
)
from fulfill.models import SideEffect, WebhookDelivery
from shopdesk.settings import HA_CONFIG_PATH


def _config() -> dict:
    return json.loads(Path(HA_CONFIG_PATH).read_text(encoding="utf-8"))


def record_capture_effect(*, attempt_id: str, order: Order) -> SideEffect:
    digest = payload_hash_for(order.order_ref, attempt_id, order.total_cents)
    _ = decide_claim(
        existing_hashes={},
        attempt_id=attempt_id,
        kind="capture",
        payload_hash=digest,
        write_lsn=order.write_lsn,
        min_committed_lsn=None,
    )
    claimed = claim_side_effect(
        attempt_id=attempt_id,
        kind="capture",
        payload_hash=digest,
        write_lsn=order.write_lsn,
    )
    if claimed.created or should_emit_webhook(
        decide_claim(
            existing_hashes={},
            attempt_id=attempt_id,
            kind="capture",
            payload_hash=digest,
            write_lsn=order.write_lsn,
            min_committed_lsn=None,
        )
    ):
        target = str(_config().get("webhook_target", "https://hooks.shopdesk.internal/capture"))
        meta = delivery_attempt_record(target=target, attempt_no=1, http_status=200)
        WebhookDelivery.objects.create(
            side_effect=claimed.row,
            target=target,
            attempt_no=int(meta["attempt_no"]),
            http_status=int(meta["http_status"]),
        )
        claimed.row.status = "DELIVERED"
        claimed.row.delivered_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        claimed.row.save(update_fields=["status", "delivered_at"])
    return claimed.row


def duplicate_effect_count() -> int:
    from django.db.models import Count

    rows = (
        SideEffect.objects.values("attempt_id", "kind")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    return int(sum(int(row["n"]) - 1 for row in rows))
