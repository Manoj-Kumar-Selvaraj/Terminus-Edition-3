#!/usr/bin/env python3
"""Generate primary and lagged-standby SQL seeds for the checkout HA lab."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATUSES = ["PLACED", "PAID", "FULFILLING", "SHIPPED", "DELIVERED", "CANCELLED", "HELD", "RETURNED"]
CHANNELS = ["web", "ios", "android", "pos", "callcenter", "affiliate", "marketplace"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"]
CATEGORIES = ["grocery", "home", "electronics", "apparel", "beauty", "outdoor", "toys", "auto"]
TIERS = ["bronze", "silver", "gold", "platinum"]
RISKS = ["low", "medium", "high", "watch"]
REGIONS = ["west", "east", "central"]
CITIES = [
    "seattle", "portland", "denver", "austin", "chicago", "atlanta",
    "boston", "miami", "phoenix", "dallas", "minneapolis", "detroit",
]
FULFILL_CLASS = ["parcel", "bulk", "cold", "hazmat"]


def q(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def emit_insert(out: list[str], table: str, cols: list[str], rows: list[tuple]) -> None:
    if not rows:
        return
    chunk = 80
    colnames = ", ".join(cols)
    for start in range(0, len(rows), chunk):
        part = rows[start : start + chunk]
        values = []
        for row in part:
            values.append("(" + ", ".join(q(v) for v in row) + ")")
        out.append(f"INSERT INTO {table} ({colnames}) VALUES\n" + ",\n".join(values) + ";")


def build() -> None:
    start = datetime(2025, 8, 9, tzinfo=timezone.utc)
    warehouses = []
    for idx in range(1, 13):
        az = "az-a" if idx % 2 else "az-b"
        warehouses.append(
            (idx, f"WH{idx:02d}", REGIONS[idx % 3], az, "open" if idx != 12 else "drain", CITIES[idx - 1])
        )
    products = []
    prices = []
    price_id = 1
    for idx in range(1, 81):
        cat = CATEGORIES[idx % len(CATEGORIES)]
        products.append(
            (idx, f"SKU-{idx:04d}", f"Item {idx}", cat, 1 if idx % 17 else 0, FULFILL_CLASS[idx % 4])
        )
        for cidx, currency in enumerate(CURRENCIES):
            unit = 199 + idx * 17 + cidx * 13 + (idx * cidx) % 89
            prices.append((price_id, idx, currency, unit, "2025-01-01"))
            price_id += 1
            prices.append((price_id, idx, currency, unit + 25, "2026-01-01"))
            price_id += 1

    shoppers = []
    addresses = []
    for idx in range(1, 5001):
        ref = f"shp-{idx:04d}"
        digest = hashlib.sha256(f"{ref}@shopdesk.example".encode("utf-8")).hexdigest()
        created = start - timedelta(days=(idx % 400), minutes=idx % 50)
        shoppers.append(
            (
                idx,
                ref,
                digest,
                REGIONS[idx % 3],
                TIERS[idx % 4],
                created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                RISKS[idx % 4],
            )
        )
        addresses.append((idx, idx, "ship", f"{10000 + (idx * 37) % 89999}", ["US", "CA", "GB", "DE", "AU"][idx % 5]))

    lots = []
    lot_id = 1
    for wid in range(1, 13):
        for pid in range(1, 81):
            lots.append((lot_id, wid, pid, f"L{wid:02d}-{pid:03d}", 80 + (wid * pid) % 40, (wid + pid) % 5))
            lot_id += 1

    carts = []
    cartlines = []
    attempts = []
    orders = []
    orderlines = []
    payments = []
    effects = []
    webhooks = []
    reservations = []
    line_id = 1
    pay_id = 1
    effect_id = 1
    hook_id = 1
    res_id = 1
    attempt_row_id = 1

    incident_attempts = {
        19990: "att-inc-20001",
        19995: "att-inc-20007",
        19999: "att-inc-20012",
    }

    for oid in range(1, 20001):
        shopper_id = 1 + (oid * 17) % 5000
        warehouse_id = 1 + (oid * 5) % 12
        product_id = 1 + (oid * 11) % 80
        qty = 1 + oid % 4
        currency = CURRENCIES[oid % 6]
        channel = CHANNELS[oid % 7]
        status = STATUSES[oid % 8]
        az = "az-a" if oid % 2 else "az-b"
        placed = start - timedelta(days=oid % 360, minutes=(oid * 3) % 1440, seconds=oid % 60)
        unit = 199 + product_id * 17 + (oid % 89)
        total = unit * qty
        write_lsn = 100 + oid
        if oid >= 19989:
            attempt_id = incident_attempts.get(oid, f"att-inc-{oid}")
            status = "PAID" if oid in incident_attempts else "PLACED"
            az = "az-b"
            write_lsn = 19810 + (oid - 19988)
        else:
            attempt_id = f"att-{oid:05d}"
        order_ref = f"ORD-{oid:05d}"
        cart_id = oid
        carts.append(
            (
                cart_id,
                shopper_id,
                warehouse_id,
                "CHECKED_OUT",
                currency,
                placed.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )
        cartlines.append((oid, cart_id, product_id, qty))
        attempts.append(
            (
                attempt_row_id,
                attempt_id,
                cart_id,
                shopper_id,
                attempt_id,
                "PLACED",
                az,
                placed.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )
        attempt_row_id += 1
        orders.append(
            (
                oid,
                order_ref,
                shopper_id,
                attempt_id,
                warehouse_id,
                status,
                channel,
                currency,
                total,
                az,
                placed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                write_lsn,
            )
        )
        orderlines.append((line_id, oid, product_id, qty, unit))
        line_id += 1
        captured = placed.strftime("%Y-%m-%dT%H:%M:%SZ") if status in {"PAID", "FULFILLING", "SHIPPED", "DELIVERED"} else None
        payments.append(
            (
                pay_id,
                oid,
                f"pay-{attempt_id}",
                "CAPTURED" if captured else "AUTHORIZED",
                total,
                captured if captured else "",
            )
        )
        pay_id += 1
        lot_index = (warehouse_id - 1) * 80 + product_id
        reservations.append(
            (
                res_id,
                lot_index,
                attempt_id,
                qty,
                "COMMITTED" if captured else "HELD",
                placed.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )
        res_id += 1
        if oid in incident_attempts or (oid % 211 == 0):
            dup = 2 if oid in incident_attempts else 1
            for n in range(dup):
                effects.append(
                    (
                        effect_id,
                        attempt_id,
                        "capture",
                        hashlib.sha256(f"{attempt_id}:{n}".encode("utf-8")).hexdigest(),
                        "DELIVERED",
                        placed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        write_lsn,
                    )
                )
                webhooks.append(
                    (hook_id, effect_id, "https://hooks.shopdesk.internal/capture", n + 1, 200)
                )
                hook_id += 1
                effect_id += 1

    primary_lsn = max(row[11] for row in orders)
    nodes = [
        ("az-a", "primary", "2026-08-08T21:18:00Z", 1),
        ("az-b", "primary", "2026-08-08T21:18:00Z", 1),
    ]
    fences = [("checkout-primary", "az-a", 3, 1, "2026-08-08T21:18:00Z")]
    # Split-brain: replica also has a writable lease for az-b after a naive apply.
    replica_fences = [
        ("checkout-primary", "az-b", 3, 1, "2026-08-08T21:18:00Z"),
    ]

    def dump(path: Path, *, standby: bool) -> None:
        out: list[str] = ["PRAGMA foreign_keys = OFF;", "BEGIN;"]
        emit_insert(out, "catalog_warehouse", ["id", "code", "region", "az_id", "status", "city"], warehouses)
        emit_insert(
            out,
            "catalog_product",
            ["id", "sku", "name", "category", "active", "fulfillment_class"],
            products,
        )
        emit_insert(
            out,
            "catalog_pricebook",
            ["id", "product_id", "currency", "unit_cents", "effective_from"],
            prices,
        )
        emit_insert(
            out,
            "identity_shopper",
            ["id", "shopper_ref", "email_hash", "region", "loyalty_tier", "created_at", "risk_band"],
            shoppers,
        )
        emit_insert(out, "identity_address", ["id", "shopper_id", "kind", "postal", "country"], addresses)
        emit_insert(
            out,
            "inventory_stocklot",
            ["id", "warehouse_id", "product_id", "lot_code", "qty_on_hand", "qty_reserved"],
            lots,
        )
        if standby:
            kept_orders = [row for row in orders if row[0] <= 19800]
            kept_ids = {row[0] for row in kept_orders}
            kept_attempts = {row[3] for row in kept_orders}
            emit_insert(
                out,
                "checkout_cart",
                ["id", "shopper_id", "warehouse_id", "status", "currency", "updated_at"],
                [row for row in carts if row[0] in kept_ids],
            )
            emit_insert(
                out,
                "checkout_cartline",
                ["id", "cart_id", "product_id", "qty"],
                [row for row in cartlines if row[1] in kept_ids],
            )
            emit_insert(
                out,
                "checkout_attempt",
                ["id", "attempt_id", "cart_id", "shopper_id", "idempotency_key", "status", "az_origin", "created_at"],
                [row for row in attempts if row[2] in kept_ids],
            )
            emit_insert(
                out,
                "checkout_order",
                [
                    "id",
                    "order_ref",
                    "shopper_id",
                    "attempt_id",
                    "warehouse_id",
                    "status",
                    "channel",
                    "currency",
                    "total_cents",
                    "az_origin",
                    "placed_at",
                    "write_lsn",
                ],
                kept_orders,
            )
            emit_insert(
                out,
                "checkout_orderline",
                ["id", "order_id", "product_id", "qty", "unit_cents"],
                [row for row in orderlines if row[1] in kept_ids],
            )
            emit_insert(
                out,
                "checkout_payment",
                ["id", "order_id", "provider_ref", "status", "amount_cents", "captured_at"],
                [tuple(v if v != "" else None for v in row) for row in payments if row[1] in kept_ids],
            )
            emit_insert(
                out,
                "inventory_reservation",
                ["id", "stocklot_id", "attempt_id", "qty", "status", "created_at"],
                [row for row in reservations if row[2] in kept_attempts],
            )
            emit_insert(
                out,
                "fulfill_side_effect",
                ["id", "attempt_id", "kind", "payload_hash", "status", "delivered_at", "write_lsn"],
                [row for row in effects if row[1] in kept_attempts],
            )
            kept_effect_ids = {row[0] for row in effects if row[1] in kept_attempts}
            emit_insert(
                out,
                "fulfill_webhook",
                ["id", "side_effect_id", "target", "attempt_no", "http_status"],
                [row for row in webhooks if row[1] in kept_effect_ids],
            )
            emit_insert(
                out,
                "ha_watermark",
                ["role", "wal_lsn", "applied_lsn", "updated_at"],
                [("replica", 0, 19800, "2026-08-08T21:18:00Z")],
            )
            emit_insert(
                out,
                "ha_fence_lease",
                ["resource", "owner_node", "epoch", "writable", "fenced_until"],
                replica_fences,
            )
            emit_insert(out, "ha_node", ["node_id", "role", "last_seen", "ready"], nodes)
        else:
            emit_insert(
                out,
                "checkout_cart",
                ["id", "shopper_id", "warehouse_id", "status", "currency", "updated_at"],
                carts,
            )
            emit_insert(
                out,
                "checkout_cartline",
                ["id", "cart_id", "product_id", "qty"],
                cartlines,
            )
            emit_insert(
                out,
                "checkout_attempt",
                ["id", "attempt_id", "cart_id", "shopper_id", "idempotency_key", "status", "az_origin", "created_at"],
                attempts,
            )
            emit_insert(
                out,
                "checkout_order",
                [
                    "id",
                    "order_ref",
                    "shopper_id",
                    "attempt_id",
                    "warehouse_id",
                    "status",
                    "channel",
                    "currency",
                    "total_cents",
                    "az_origin",
                    "placed_at",
                    "write_lsn",
                ],
                orders,
            )
            emit_insert(
                out,
                "checkout_orderline",
                ["id", "order_id", "product_id", "qty", "unit_cents"],
                orderlines,
            )
            pay_rows = []
            for row in payments:
                vals = list(row)
                vals[5] = vals[5] or None
                pay_rows.append(tuple(vals))
            emit_insert(
                out,
                "checkout_payment",
                ["id", "order_id", "provider_ref", "status", "amount_cents", "captured_at"],
                pay_rows,
            )
            emit_insert(
                out,
                "inventory_reservation",
                ["id", "stocklot_id", "attempt_id", "qty", "status", "created_at"],
                reservations,
            )
            emit_insert(
                out,
                "fulfill_side_effect",
                ["id", "attempt_id", "kind", "payload_hash", "status", "delivered_at", "write_lsn"],
                effects,
            )
            emit_insert(
                out,
                "fulfill_webhook",
                ["id", "side_effect_id", "target", "attempt_no", "http_status"],
                webhooks,
            )
            emit_insert(
                out,
                "ha_watermark",
                ["role", "wal_lsn", "applied_lsn", "updated_at"],
                [
                    ("primary", primary_lsn, primary_lsn, "2026-08-08T21:18:00Z"),
                    ("replica", 0, 0, "2026-08-08T21:18:00Z"),
                ],
            )
            emit_insert(
                out,
                "ha_fence_lease",
                ["resource", "owner_node", "epoch", "writable", "fenced_until"],
                fences,
            )
            emit_insert(out, "ha_node", ["node_id", "role", "last_seen", "ready"], nodes)
        out.append("COMMIT;")
        path.write_text("\n".join(out) + "\n", encoding="utf-8")

    dump(HERE / "seed.sql", standby=False)
    dump(HERE / "standby_seed.sql", standby=True)


if __name__ == "__main__":
    build()
