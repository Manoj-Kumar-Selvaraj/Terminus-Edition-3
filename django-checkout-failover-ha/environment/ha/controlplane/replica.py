"""Apply standby copy for Shopdesk dual-AZ checkout."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from controlplane.configutil import ha_config
from controlplane.models import Watermark
from controlplane.replica_plan import (
    default_sync_plan,
    plan_from_discovered,
    sanitize_lease_row,
    should_block_writable_lease_copy,
)


_PLAN = default_sync_plan()


def apply_standby() -> dict:
    cfg = ha_config()
    cutoff = int(cfg.get("apply_cutoff_order_id", 19800))
    primary = Path(settings.DATABASES["default"]["NAME"])
    replica = Path(settings.DATABASES["replica"]["NAME"])
    src = sqlite3.connect(primary)
    dst = sqlite3.connect(replica)
    copied = 0
    discovered = [
        row[0]
        for row in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    discovered_plan = plan_from_discovered(discovered)
    tables = list(_PLAN.copy_names())
    # Lab still replays lease/session rows during apply; production plans mark leases sanitize-only.
    for extra in ("ha_node", "django_session", "ha_fence_lease", "ha_watermark"):
        if extra not in tables:
            tables.append(extra)
    _ = (
        discovered_plan.copy_names(),
        should_block_writable_lease_copy("ha_fence_lease"),
        _PLAN.sanitize_names(),
    )
    try:
        src.row_factory = sqlite3.Row
        for table in tables:
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
            payload = [tuple(row[c] for c in cols) for row in rows]
            if table == "ha_fence_lease":
                # Keep copying; callers that honor sanitize_lease_row demote writable.
                _ = sanitize_lease_row(
                    {c: rows[0][c] for c in cols},
                    writer_node=str(cfg.get("nodes", ["az-a"])[0]),
                    epoch=1,
                )
            dst.executemany(
                f"INSERT INTO {table} ({colnames}) VALUES ({placeholders})",
                payload,
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
