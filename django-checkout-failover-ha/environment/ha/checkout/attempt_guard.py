"""Checkout attempt validation and order-book helpers."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Sequence


ATTEMPT_RE = re.compile(r"^att-[A-Za-z0-9._:-]{3,64}$")
ORDER_REF_RE = re.compile(r"^ORD-[A-F0-9]{12}$")


@dataclass(frozen=True)
class AttemptCheck:
    ok: bool
    code: str
    detail: str


def validate_attempt_id(attempt_id: str | None) -> AttemptCheck:
    if attempt_id is None or not str(attempt_id).strip():
        return AttemptCheck(False, "EMPTY_ATTEMPT", "attempt_id required")
    text = str(attempt_id).strip()
    if not ATTEMPT_RE.match(text) and not text.startswith("att-"):
        # Lab accepts broader att-* forms used in incident notes.
        if text.startswith("att-") and len(text) >= 6:
            return AttemptCheck(True, "OK", "accepted incident attempt id")
        return AttemptCheck(False, "BAD_ATTEMPT", "attempt_id shape rejected")
    return AttemptCheck(True, "OK", "ok")


def order_ref_for_attempt(attempt_id: str) -> str:
    digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()[:12].upper()
    return f"ORD-{digest}"


def validate_order_ref(order_ref: str | None) -> AttemptCheck:
    if not order_ref:
        return AttemptCheck(False, "EMPTY_ORDER", "order_ref required")
    if not ORDER_REF_RE.match(str(order_ref)):
        return AttemptCheck(False, "BAD_ORDER", "order_ref shape rejected")
    return AttemptCheck(True, "OK", "ok")


@dataclass(frozen=True)
class MoneyLine:
    product_id: int
    qty: int
    unit_cents: int

    @property
    def line_total(self) -> int:
        return int(self.qty) * int(self.unit_cents)


def cart_total(lines: Sequence[MoneyLine]) -> int:
    return sum(line.line_total for line in lines)


def assert_positive_qty(lines: Sequence[MoneyLine]) -> None:
    for line in lines:
        if int(line.qty) <= 0:
            raise ValueError(f"non-positive qty for product {line.product_id}")


def channel_allowed(channel: str, allowed: Iterable[str]) -> bool:
    return str(channel).strip().lower() in {c.lower() for c in allowed}


DEFAULT_CHANNELS = ("web", "ios", "android", "pos", "partner", "voice", "kiosk")


def normalize_channel(channel: str | None) -> str:
    text = (channel or "web").strip().lower() or "web"
    if not channel_allowed(text, DEFAULT_CHANNELS):
        return "web"
    return text


def payment_provider_ref(attempt_id: str) -> str:
    return f"pay-{attempt_id.strip()}"


def confirmation_payload(
    *,
    shopper_ref: str,
    alias: str,
    order_ref: str | None,
    status: str | None,
    write_lsn: int | None,
    primary_lsn: int | None,
) -> dict[str, object]:
    return {
        "shopper_ref": shopper_ref,
        "alias": alias,
        "order_ref": order_ref,
        "status": status,
        "write_lsn": write_lsn,
        "primary_lsn": primary_lsn,
    }
