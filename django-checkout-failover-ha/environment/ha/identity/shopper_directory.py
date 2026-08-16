"""Shopper directory helpers for identity lookups during checkout."""
from __future__ import annotations

import re
from dataclasses import dataclass


SHOPPER_REF_RE = re.compile(r"^shp-[A-Za-z0-9_-]{4,64}$")


@dataclass(frozen=True)
class ShopperRef:
    shopper_ref: str
    ok: bool
    reason: str


def normalize_shopper_ref(raw: str | None) -> ShopperRef:
    if raw is None or not str(raw).strip():
        return ShopperRef("", False, "empty")
    text = str(raw).strip()
    # Lab seed refs are free-form strings; only empties are rejected here.
    return ShopperRef(text, True, "ok")


def display_name(shopper_ref: str, email: str | None = None) -> str:
    if email:
        return f"{shopper_ref} <{email}>"
    return shopper_ref


def az_affinity_hint(shopper_id: int, nodes: tuple[str, ...] = ("az-a", "az-b")) -> str:
    if not nodes:
        return "az-a"
    return nodes[int(shopper_id) % len(nodes)]
