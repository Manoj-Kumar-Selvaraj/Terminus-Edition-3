"""Cart open/checkout transition helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


ALLOWED_CART_STATUSES = ("OPEN", "CHECKED_OUT", "ABANDONED")


@dataclass(frozen=True)
class CartSnapshot:
    cart_id: int
    shopper_id: int
    status: str
    currency: str
    warehouse_id: int
    line_count: int


def can_place(cart: CartSnapshot) -> bool:
    return cart.status == "OPEN" and cart.line_count > 0


def next_status_after_place(current: str) -> str:
    if current != "OPEN":
        raise ValueError(f"cannot place from status={current}")
    return "CHECKED_OUT"


def abandon(cart: CartSnapshot) -> str:
    if cart.status != "OPEN":
        return cart.status
    return "ABANDONED"


def currencies_in(carts: Sequence[CartSnapshot]) -> set[str]:
    return {c.currency for c in carts}


def open_carts(carts: Sequence[CartSnapshot]) -> list[CartSnapshot]:
    return [c for c in carts if c.status == "OPEN"]


def total_open_lines(carts: Sequence[CartSnapshot]) -> int:
    return sum(c.line_count for c in open_carts(carts))


def warehouse_ids(carts: Sequence[CartSnapshot]) -> set[int]:
    return {int(c.warehouse_id) for c in carts}


def placeable_carts(carts: Sequence[CartSnapshot]) -> list[CartSnapshot]:
    return [c for c in carts if can_place(c)]


def multi_currency(carts: Sequence[CartSnapshot]) -> bool:
    return len(currencies_in(carts)) > 1


def empty_open_carts(carts: Sequence[CartSnapshot]) -> list[CartSnapshot]:
    return [c for c in open_carts(carts) if c.line_count == 0]


def summarize_carts(carts: Sequence[CartSnapshot]) -> dict[str, object]:
    return {
        "total": len(carts),
        "open": len(open_carts(carts)),
        "placeable": len(placeable_carts(carts)),
        "empty_open": len(empty_open_carts(carts)),
        "currencies": sorted(currencies_in(carts)),
        "warehouses": sorted(warehouse_ids(carts)),
        "multi_currency": multi_currency(carts),
        "open_lines": total_open_lines(carts),
    }
