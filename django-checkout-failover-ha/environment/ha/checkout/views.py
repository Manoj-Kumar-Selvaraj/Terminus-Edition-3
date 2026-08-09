from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from checkout.models import Order, OrderLine, Payment
from checkout.services import CheckoutError
from checkout.services import capture_payment as capture_payment_service
from checkout.services import confirmation_for
from checkout.services import place_order as place_order_service


def _body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _error(exc: Exception) -> JsonResponse:
    status = 400 if isinstance(exc, CheckoutError) else 409
    return JsonResponse({"ok": False, "error": str(exc)}, status=status)


@csrf_exempt
def place_order(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    payload = _body(request)
    try:
        order = place_order_service(
            shopper_ref=str(payload.get("shopper_ref", "")),
            attempt_id=str(payload.get("attempt_id", "")),
            channel=str(payload.get("channel") or "web"),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)
    return JsonResponse(
        {
            "ok": True,
            "order_ref": order.order_ref,
            "status": order.status,
            "write_lsn": order.write_lsn,
            "attempt_id": order.attempt_id,
        }
    )


def order_detail(request: HttpRequest, order_ref: str) -> HttpResponse:
    order = Order.objects.filter(order_ref=order_ref).first()
    if order is None:
        return JsonResponse({"ok": False, "error": "unknown order"}, status=404)
    lines = [
        {"product_id": line.product_id, "qty": line.qty, "unit_cents": line.unit_cents}
        for line in OrderLine.objects.filter(order=order)
    ]
    payment = Payment.objects.filter(order=order).order_by("-id").first()
    return JsonResponse(
        {
            "ok": True,
            "order_ref": order.order_ref,
            "status": order.status,
            "total_cents": order.total_cents,
            "attempt_id": order.attempt_id,
            "lines": lines,
            "payment_status": None if payment is None else payment.status,
        }
    )


@csrf_exempt
def capture_payment(request: HttpRequest, order_ref: str) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    try:
        payment = capture_payment_service(order_ref)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)
    return JsonResponse(
        {
            "ok": True,
            "order_ref": order_ref,
            "payment_status": payment.status,
            "captured_at": payment.captured_at,
        }
    )


def confirmation(request: HttpRequest, shopper_ref: str) -> HttpResponse:
    try:
        payload = confirmation_for(shopper_ref)
    except CheckoutError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=404)
    payload["ok"] = True
    return JsonResponse(payload)
