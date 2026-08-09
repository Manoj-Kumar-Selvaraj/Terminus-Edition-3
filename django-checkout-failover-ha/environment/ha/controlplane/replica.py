"""Starter apply-standby: hardcoded cutoff and copies fence leases."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from controlplane.configutil import ha_config
from controlplane.models import Watermark


BUSINESS_TABLES = [
    "catalog_warehouse",
    "catalog_product",
    "catalog_pricebook",
    "identity_shopper",
    "identity_address",
    "inventory_stocklot",
    "inventory_reservation",
    "checkout_cart",
    "checkout_cartline",
    "checkout_attempt",
    "checkout_order",
    "checkout_orderline",
    "checkout_payment",
    "fulfill_side_effect",
    "fulfill_webhook",
    "django_session",
    "ha_node",
    "ha_fence_lease",
    "ha_watermark",
]


def apply_standby() -> dict:
    cfg = ha_config()
    cutoff = int(cfg.get("apply_cutoff_order_id", 19800))
    primary = Path(settings.DATABASES["default"]["NAME"])
    replica = Path(settings.DATABASES["replica"]["NAME"])
    src = sqlite3.connect(primary)
    dst = sqlite3.connect(replica)
    copied = 0
    try:
        src.row_factory = sqlite3.Row
        for table in BUSINESS_TABLES:
            if table == "checkout_order":
                rows = src.execute(
                    "SELECT * FROM checkout_order WHERE id <= ?", (cutoff,)
                ).fetchall()
            else:
                rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue
            cols = rows[0].keys()
            placeholders = ",".join("?" for _ in cols)
            colnames = ",".join(cols)
            dst.execute(f"DELETE FROM {table}")
            dst.executemany(
                f"INSERT INTO {table} ({colnames}) VALUES ({placeholders})",
                [tuple(row[c] for c in cols) for row in rows],
            )
            copied += len(rows)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dst.execute(
            "INSERT OR REPLACE INTO ha_watermark(role, wal_lsn, applied_lsn, updated_at) "
            "VALUES ('replica', 0, ?, ?)",
            (cutoff, now),
        )
        dst.commit()
    finally:
        src.close()
        dst.close()
    mark = Watermark.objects.using("replica").filter(role="replica").first()
    return {"copied": copied, "applied_lsn": 0 if mark is None else int(mark.applied_lsn)}
