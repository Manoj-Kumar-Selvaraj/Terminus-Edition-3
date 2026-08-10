from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction

from catalog.pricing import current_unit_cents
from checkout.models import Cart, CartLine, CheckoutAttempt, Order, OrderLine, Payment
from controlplane.fencing import FenceError, assert_can_write, bump_primary_lsn, current_lsn
from controlplane.sessions import set_sticky_pin
from fulfill.services import record_capture_effect
from identity.models import Shopper
from inventory.services import already_committed, commit_reservation, reserve_for_attempt


class CheckoutError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _order_ref(attempt_id: str) -> str:
    digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()[:12].upper()
    return f"ORD-{digest}"


def place_order(*, shopper_ref: str, attempt_id: str, channel: str = "web") -> Order:
    if not attempt_id or not attempt_id.strip():
        raise CheckoutError("attempt_id required")
    shopper = Shopper.objects.filter(shopper_ref=shopper_ref).first()
    if shopper is None:
        raise CheckoutError("unknown shopper")
    existing = Order.objects.filter(attempt_id=attempt_id).first()
    if existing is not None:
        record_capture_effect(attempt_id=attempt_id, order=existing)
        set_sticky_pin(shopper.id)
        return existing
    cart = Cart.objects.filter(shopper=shopper, status="OPEN").order_by("-id").first()
    if cart is None:
        raise CheckoutError("no open cart")
    lines = list(CartLine.objects.filter(cart=cart))
    if not lines:
        raise CheckoutError("empty cart")
    assert_can_write(getattr(settings, "AZ_ID", "az-a"))
    with transaction.atomic(using="default"):
        attempt, _ = CheckoutAttempt.objects.get_or_create(
            attempt_id=attempt_id,
            defaults={
                "cart": cart,
                "shopper": shopper,
                "idempotency_key": attempt_id,
                "status": "PLACING",
                "az_origin": getattr(settings, "AZ_ID", "az-a"),
                "created_at": _now(),
            },
        )
        total = 0
        built_lines: list[tuple[int, int, int]] = []
        for line in lines:
            unit = current_unit_cents(line.product, cart.currency)
            reserve_for_attempt(cart.warehouse_id, line.product_id, line.qty, attempt_id)
            total += unit * int(line.qty)
            built_lines.append((line.product_id, int(line.qty), unit))
        lsn = bump_primary_lsn()
        order = Order.objects.create(
            order_ref=_order_ref(attempt_id),
            shopper=shopper,
            attempt_id=attempt_id,
            warehouse=cart.warehouse,
            status="PLACED",
            channel=channel,
            currency=cart.currency,
            total_cents=total,
            az_origin=getattr(settings, "AZ_ID", "az-a"),
            placed_at=_now(),
            write_lsn=lsn,
        )
        for product_id, qty, unit in built_lines:
            OrderLine.objects.create(order=order, product_id=product_id, qty=qty, unit_cents=unit)
        Payment.objects.create(
            order=order,
            provider_ref=f"pay-{attempt_id}",
            status="AUTHORIZED",
            amount_cents=total,
            captured_at=None,
        )
        attempt.status = "PLACED"
        attempt.save(update_fields=["status"])
        cart.status = "CHECKED_OUT"
        cart.updated_at = _now()
        cart.save(update_fields=["status", "updated_at"])
    record_capture_effect(attempt_id=attempt_id, order=order)
    set_sticky_pin(shopper.id)
    return order


def capture_payment(order_ref: str) -> Payment:
    order = Order.objects.filter(order_ref=order_ref).first()
    if order is None:
        raise CheckoutError("unknown order")
    assert_can_write(getattr(settings, "AZ_ID", "az-a"))
    payment = Payment.objects.filter(order=order).order_by("-id").first()
    if payment is None:
        raise CheckoutError("missing payment")
    if payment.status == "CAPTURED":
        record_capture_effect(attempt_id=order.attempt_id, order=order)
        return payment
    with transaction.atomic(using="default"):
        payment.status = "CAPTURED"
        payment.captured_at = _now()
        payment.save(update_fields=["status", "captured_at"])
        order.status = "PAID"
        order.write_lsn = bump_primary_lsn()
        order.save(update_fields=["status", "write_lsn"])
        if not already_committed(order.attempt_id):
            commit_reservation(order.attempt_id)
    record_capture_effect(attempt_id=order.attempt_id, order=order)
    set_sticky_pin(order.shopper_id)
    return payment


def confirmation_for(shopper_ref: str):
    from controlplane.router import read_alias_for_shopper

    shopper = Shopper.objects.filter(shopper_ref=shopper_ref).first()
    if shopper is None:
        raise CheckoutError("unknown shopper")
    alias = read_alias_for_shopper(shopper.id)
    order = Order.objects.using(alias).filter(shopper=shopper).order_by("-id").first()
    return {
        "shopper_ref": shopper_ref,
        "alias": alias,
        "order_ref": None if order is None else order.order_ref,
        "status": None if order is None else order.status,
        "write_lsn": None if order is None else order.write_lsn,
        "primary_lsn": current_lsn("primary"),
    }
