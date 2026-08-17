#!/usr/bin/env python3
"""Deterministic click warehouse + operator catalog for /app/sessions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
WAREHOUSE = ROOT / "warehouse"
LEDGER = WAREHOUSE / "click_ledger.jsonl"
SEED_SQL = SQL_DIR / "seed.sql"
SCHEMA_SQL = SQL_DIR / "schema.sql"
CATALOG = WAREHOUSE / "catalog.sqlite"

REGIONS = ("us-east", "us-west", "eu-west", "ap-south")
PLANS = ("standard", "enterprise", "internal")
COHORTS = ("new", "returning", "power", "churn-risk")
CHANNELS = ("web", "ios", "android", "email", "kiosk", "partner")
KINDS = (
    "page_view",
    "click",
    "scroll",
    "cart_add",
    "cart_remove",
    "checkout_start",
    "search",
    "heartbeat",
)
DEVICES = tuple(f"d{i:02d}" for i in range(12))
COUNTRIES = (
    "US",
    "CA",
    "GB",
    "DE",
    "FR",
    "IN",
    "JP",
    "AU",
    "BR",
    "MX",
    "NL",
    "SE",
    "SG",
    "KR",
    "ZA",
)
SOURCES = ("collector-a", "collector-b", "replay-desk", "partner-in")


def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def events():
    n = 0
    for tenant_i in range(40):
        tenant = f"t{tenant_i:02d}"
        region = REGIONS[tenant_i % len(REGIONS)]
        plan = PLANS[tenant_i % len(PLANS)]
        yield ("tenant", tenant, region, plan, 900_000 + tenant_i * 100)
        yield (
            "batch",
            tenant_i + 1,
            tenant,
            SOURCES[tenant_i % len(SOURCES)],
            950_000 + tenant_i * 25,
        )
        for user_i in range(15):
            user = f"u{user_i:03d}"
            cohort = COHORTS[(tenant_i + user_i) % len(COHORTS)]
            base = 1_000_000 + tenant_i * 50_000 + user_i * 1_000
            yield ("user", tenant, user, cohort, base)
            for k in range(20):
                n += 1
                kind = KINDS[(tenant_i + user_i + k) % len(KINDS)]
                channel = CHANNELS[(user_i + k) % len(CHANNELS)]
                page = f"/p/{(n - 1) % 80}"
                device = DEVICES[(user_i + k) % len(DEVICES)]
                country = COUNTRIES[(tenant_i + k) % len(COUNTRIES)]
                event_time = base + k * 8_000 + (k % 3) * 17
                payload = f"{kind}:{page}:{k}:{channel}"
                yield {
                    "event_id": f"w{n:05d}",
                    "tenant_id": tenant,
                    "user_id": user,
                    "event_time_ms": event_time,
                    "payload": payload,
                    "channel": channel,
                    "kind": kind,
                    "page": page,
                    "device": device,
                    "country": country,
                    "ingest_batch_id": tenant_i + 1,
                }


def write_ledger_and_sql() -> int:
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    tenants: list[tuple] = []
    users: list[tuple] = []
    batches: list[tuple] = []
    rows: list[dict] = []
    for item in events():
        if isinstance(item, tuple) and item[0] == "tenant":
            tenants.append(item[1:])
        elif isinstance(item, tuple) and item[0] == "user":
            users.append(item[1:])
        elif isinstance(item, tuple) and item[0] == "batch":
            batches.append(item[1:])
        else:
            rows.append(item)

    with LEDGER.open("w", encoding="utf-8") as fh:
        for obj in rows:
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    parts: list[str] = ["BEGIN;"]
    for tenant_id, region, plan, created in tenants:
        parts.append(
            "INSERT INTO tenant (tenant_id, region, plan, created_event_time_ms) VALUES ("
            f"{sql_str(tenant_id)}, {sql_str(region)}, {sql_str(plan)}, {int(created)});"
        )
    for batch_id, tenant_id, source, recorded in batches:
        parts.append(
            "INSERT INTO ingest_batch (batch_id, tenant_id, source, recorded_at_ms) VALUES ("
            f"{int(batch_id)}, {sql_str(tenant_id)}, {sql_str(source)}, {int(recorded)});"
        )
    for tenant_id, user_id, cohort, first_seen in users:
        parts.append(
            "INSERT INTO click_user (tenant_id, user_id, cohort, first_seen_ms) VALUES ("
            f"{sql_str(tenant_id)}, {sql_str(user_id)}, {sql_str(cohort)}, {int(first_seen)});"
        )
    chunk: list[str] = []
    cols = (
        "event_id, tenant_id, user_id, event_time_ms, payload, channel, kind, "
        "page, device, country, ingest_batch_id"
    )
    for obj in rows:
        chunk.append(
            "("
            f"{sql_str(obj['event_id'])}, {sql_str(obj['tenant_id'])}, "
            f"{sql_str(obj['user_id'])}, {int(obj['event_time_ms'])}, "
            f"{sql_str(obj['payload'])}, {sql_str(obj['channel'])}, "
            f"{sql_str(obj['kind'])}, {sql_str(obj['page'])}, "
            f"{sql_str(obj['device'])}, {sql_str(obj['country'])}, "
            f"{int(obj['ingest_batch_id'])})"
        )
        if len(chunk) == 80:
            parts.append(f"INSERT INTO click_event ({cols}) VALUES\n" + ",\n".join(chunk) + ";")
            chunk = []
    if chunk:
        parts.append(f"INSERT INTO click_event ({cols}) VALUES\n" + ",\n".join(chunk) + ";")
    parts.append("COMMIT;")
    SEED_SQL.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return len(rows)


def write_catalog(n_events: int) -> None:
    if CATALOG.exists():
        CATALOG.unlink()
    con = sqlite3.connect(str(CATALOG))
    try:
        con.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        con.executescript(SEED_SQL.read_text(encoding="utf-8"))
        got = con.execute("SELECT COUNT(*) FROM click_event").fetchone()[0]
        if int(got) != int(n_events):
            raise SystemExit(f"catalog row count {got} != ledger {n_events}")
        con.commit()
    finally:
        con.close()


def main() -> None:
    n = write_ledger_and_sql()
    write_catalog(n)
    print(f"wrote {n} click events to {LEDGER} and {CATALOG}")


if __name__ == "__main__":
    main()
