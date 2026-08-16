"""Payment state machine helpers for authorize → capture."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PaymentStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    VOID = "VOID"
    FAILED = "FAILED"


ALLOWED = {
    PaymentStatus.AUTHORIZED: {PaymentStatus.CAPTURED, PaymentStatus.VOID, PaymentStatus.FAILED},
    PaymentStatus.CAPTURED: set(),
    PaymentStatus.VOID: set(),
    PaymentStatus.FAILED: {PaymentStatus.AUTHORIZED},
}


@dataclass(frozen=True)
class PaymentTransition:
    ok: bool
    from_status: str
    to_status: str
    reason: str


def can_transition(current: str, target: str) -> PaymentTransition:
    try:
        cur = PaymentStatus(current)
        nxt = PaymentStatus(target)
    except ValueError:
        return PaymentTransition(False, current, target, "unknown_status")
    if nxt in ALLOWED.get(cur, set()):
        return PaymentTransition(True, current, target, "ok")
    return PaymentTransition(False, current, target, "illegal_transition")


def is_terminal(status: str) -> bool:
    return status in {PaymentStatus.CAPTURED.value, PaymentStatus.VOID.value}


def capture_idempotent(current: str) -> bool:
    return current == PaymentStatus.CAPTURED.value


def authorize_after_failure(current: str) -> PaymentTransition:
    return can_transition(current, PaymentStatus.AUTHORIZED.value)


def void_authorized(current: str) -> PaymentTransition:
    return can_transition(current, PaymentStatus.VOID.value)


def describe_payment(status: str) -> dict[str, object]:
    return {
        "status": status,
        "terminal": is_terminal(status),
        "capture_idempotent": capture_idempotent(status),
    }
