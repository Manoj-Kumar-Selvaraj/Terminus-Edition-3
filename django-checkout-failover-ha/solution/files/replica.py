from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

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
]


def apply_standby() -> dict:
    primary = Path(settings.DATABASES["default"]["NAME"])
    replica = Path(settings.DATABASES["replica"]["NAME"])
    src = sqlite3.connect(primary)
    dst = sqlite3.connect(replica)
    copied = 0
    applied_lsn = 0
    try:
        src.row_factory = sqlite3.Row
        primary_mark = src.execute(
            "SELECT wal_lsn FROM ha_watermark WHERE role='primary'"
        ).fetchone()
        applied_lsn = 0 if primary_mark is None else int(primary_mark["wal_lsn"])
        for table in BUSINESS_TABLES:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            cols = None
            dst.execute(f"DELETE FROM {table}")
            if not rows:
                continue
            cols = rows[0].keys()
            placeholders = ",".join("?" for _ in cols)
            colnames = ",".join(cols)
            dst.executemany(
                f"INSERT INTO {table} ({colnames}) VALUES ({placeholders})",
                [tuple(row[c] for c in cols) for row in rows],
            )
            copied += len(rows)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dst.execute(
            "INSERT OR REPLACE INTO ha_watermark(role, wal_lsn, applied_lsn, updated_at) "
            "VALUES ('replica', 0, ?, ?)",
            (applied_lsn, now),
        )
        dst.execute(
            "UPDATE ha_fence_lease SET writable=0 WHERE resource='checkout-primary'"
        )
        dst.commit()
    finally:
        src.close()
        dst.close()
    mark = Watermark.objects.using("replica").filter(role="replica").first()
    return {"copied": copied, "applied_lsn": 0 if mark is None else int(mark.applied_lsn)}
