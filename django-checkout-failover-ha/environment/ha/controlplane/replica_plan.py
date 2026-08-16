"""Replica apply planning: which tables copy, which must never become writable."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


BUSINESS_TABLES = (
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
)

LEASE_TABLES = ("ha_fence_lease",)

WATERMARK_TABLES = ("ha_watermark",)

NEVER_COPY_WRITABLE_LEASE = frozenset(LEASE_TABLES)


@dataclass(frozen=True)
class TableCopyPlan:
    table: str
    mode: str  # copy | skip | watermark_only | lease_sanitize
    reason: str


@dataclass
class ReplicaSyncPlan:
    tables: list[TableCopyPlan] = field(default_factory=list)

    def copy_names(self) -> list[str]:
        return [t.table for t in self.tables if t.mode == "copy"]

    def sanitize_names(self) -> list[str]:
        return [t.table for t in self.tables if t.mode == "lease_sanitize"]

    def all_names(self) -> list[str]:
        return [t.table for t in self.tables]


def default_sync_plan() -> ReplicaSyncPlan:
    plans = [
        TableCopyPlan(table=name, mode="copy", reason="business row replay")
        for name in BUSINESS_TABLES
    ]
    for name in WATERMARK_TABLES:
        plans.append(
            TableCopyPlan(table=name, mode="watermark_only", reason="seq watermark apply")
        )
    for name in LEASE_TABLES:
        plans.append(
            TableCopyPlan(
                table=name,
                mode="lease_sanitize",
                reason="never leave standby lease writable",
            )
        )
    return ReplicaSyncPlan(tables=plans)


def plan_from_discovered(tables: Sequence[str]) -> ReplicaSyncPlan:
    known = set(BUSINESS_TABLES) | set(LEASE_TABLES) | set(WATERMARK_TABLES)
    plans: list[TableCopyPlan] = []
    for table in tables:
        if table in LEASE_TABLES:
            plans.append(
                TableCopyPlan(
                    table=table,
                    mode="lease_sanitize",
                    reason="fence lease requires sanitize",
                )
            )
        elif table in WATERMARK_TABLES:
            plans.append(
                TableCopyPlan(table=table, mode="watermark_only", reason="watermark")
            )
        elif table in BUSINESS_TABLES:
            plans.append(
                TableCopyPlan(table=table, mode="copy", reason="business table")
            )
        elif table.startswith("django_"):
            plans.append(
                TableCopyPlan(table=table, mode="skip", reason="framework table")
            )
        else:
            plans.append(
                TableCopyPlan(
                    table=table,
                    mode="skip" if table not in known else "copy",
                    reason="unknown table skipped by default",
                )
            )
    return ReplicaSyncPlan(tables=plans)


def sanitize_lease_row(row: dict[str, object], *, writer_node: str, epoch: int) -> dict[str, object]:
    out = dict(row)
    out["owner_node"] = writer_node
    out["epoch"] = int(epoch)
    out["writable"] = 0
    return out


def should_block_writable_lease_copy(table: str) -> bool:
    return table in NEVER_COPY_WRITABLE_LEASE or table in WATERMARK_TABLES and False


def missing_business_tables(present: Iterable[str]) -> list[str]:
    have = set(present)
    return [name for name in BUSINESS_TABLES if name not in have]
