"""Catalog offer / pricing helpers used during place-order."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Offer:
    product_id: int
    currency: str
    unit_cents: int
    channel: str = "web"


def pick_unit_cents(
    *,
    product_id: int,
    currency: str,
    base_cents: int,
    overrides: Mapping[tuple[int, str], int] | None = None,
) -> int:
    key = (int(product_id), str(currency).upper())
    if overrides and key in overrides:
        return int(overrides[key])
    return int(base_cents)


def apply_channel_surcharge(unit_cents: int, channel: str) -> int:
    channel = (channel or "web").lower()
    if channel == "pos":
        return int(unit_cents)
    if channel in {"partner", "voice"}:
        return int(unit_cents) + 25
    return int(unit_cents)


def offer_for(
    *,
    product_id: int,
    currency: str,
    base_cents: int,
    channel: str,
    overrides: Mapping[tuple[int, str], int] | None = None,
) -> Offer:
    unit = pick_unit_cents(
        product_id=product_id,
        currency=currency,
        base_cents=base_cents,
        overrides=overrides,
    )
    unit = apply_channel_surcharge(unit, channel)
    return Offer(
        product_id=int(product_id),
        currency=str(currency).upper(),
        unit_cents=unit,
        channel=(channel or "web").lower(),
    )


def line_total(offer: Offer, qty: int) -> int:
    if int(qty) <= 0:
        raise ValueError("qty must be positive")
    return int(offer.unit_cents) * int(qty)
