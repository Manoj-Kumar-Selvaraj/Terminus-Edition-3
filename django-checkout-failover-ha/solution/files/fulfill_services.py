from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from checkout.models import Order
from controlplane.fencing import current_lsn
from controlplane.idempotency import claim_side_effect
from fulfill.models import SideEffect, WebhookDelivery
from shopdesk.settings import HA_CONFIG_PATH


def _config() -> dict:
    return json.loads(Path(HA_CONFIG_PATH).read_text(encoding="utf-8"))


def record_capture_effect(*, attempt_id: str, order: Order) -> SideEffect:
    payload = {
        "attempt_id": attempt_id,
        "order_ref": order.order_ref,
        "total_cents": order.total_cents,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    primary_lsn = current_lsn("primary")
    if int(order.write_lsn) > int(primary_lsn):
        raise RuntimeError("effect before primary commit")
    claimed = claim_side_effect(
        attempt_id=attempt_id,
        kind="capture",
        payload_hash=digest,
        write_lsn=order.write_lsn,
    )
    if claimed.created:
        target = str(_config().get("webhook_target", "https://hooks.shopdesk.internal/capture"))
        WebhookDelivery.objects.using("default").create(
            side_effect=claimed.row,
            target=target,
            attempt_no=1,
            http_status=200,
        )
        claimed.row.status = "DELIVERED"
        claimed.row.delivered_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        claimed.row.save(using="default", update_fields=["status", "delivered_at"])
    return claimed.row


def duplicate_effect_count() -> int:
    from django.db.models import Count

    rows = (
        SideEffect.objects.using("default")
        .values("attempt_id", "kind")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    return int(sum(int(row["n"]) - 1 for row in rows))
