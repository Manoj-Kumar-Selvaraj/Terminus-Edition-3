from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReasonRule:
    code: str
    allowed_types: frozenset[str]
    value_multiplier: Decimal
    audit_class: str


REASON_RULES = {
    "PO": ReasonRule("PO", frozenset({"RECEIPT"}), Decimal("1.00"), "PROCUREMENT"),
    "SALE": ReasonRule("SALE", frozenset({"ISSUE"}), Decimal("1.00"), "CUSTOMER"),
    "MOVE": ReasonRule("MOVE", frozenset({"TRANSFER"}), Decimal("1.00"), "INTERNAL"),
    "COUNT": ReasonRule("COUNT", frozenset({"ADJUSTMENT"}), Decimal("1.00"), "CYCLE_COUNT"),
    "DAMAGE": ReasonRule("DAMAGE", frozenset({"ADJUSTMENT"}), Decimal("1.00"), "SHRINK"),
    "RETURN": ReasonRule(
        "RETURN",
        frozenset({"ADJUSTMENT", "RECEIPT"}),
        Decimal("1.00"),
        "RETURN",
    ),
}


def reason_allowed(code: str, movement_type: str) -> bool:
    rule = REASON_RULES.get(code)
    return bool(rule and movement_type in rule.allowed_types)


def audit_class(code: str) -> str:
    rule = REASON_RULES.get(code)
    if rule is None:
        raise ValueError(f"unknown reason {code}")
    return rule.audit_class


def _numeric_suffix(value: str, prefix: str) -> int:
    if not value.startswith(prefix):
        raise ValueError(f"{value!r} does not start with {prefix!r}")
    suffix = value[len(prefix) :]
    if not suffix.isdigit():
        raise ValueError(f"{value!r} has no numeric suffix")
    return int(suffix)


def warehouse_class(warehouse_id: str) -> str:
    """Classify the configured 80-warehouse cutover estate without lookup padding."""
    try:
        number = _numeric_suffix(warehouse_id, "W")
    except ValueError:
        return "UNKNOWN"
    if 1 <= number <= 8:
        return "PRIMARY"
    if 9 <= number <= 80:
        return "EXTENDED"
    return "UNKNOWN"


def item_band(item_id: str) -> tuple[Decimal, str]:
    """Return the 100-item cost band used by historical cutover controls."""
    number = _numeric_suffix(item_id, "SKU")
    if not 1 <= number <= 10_000:
        raise ValueError("item outside configured bands")
    band = ((number - 1) // 100) + 1
    multiplier = Decimal("1.00") + (Decimal(band) / Decimal("100"))
    return multiplier.quantize(Decimal("0.01")), f"BAND-{band:03d}"


def expected_effect_count(movement_type: str) -> int:
    if movement_type not in {"RECEIPT", "ISSUE", "TRANSFER", "ADJUSTMENT"}:
        raise ValueError(f"unknown movement type {movement_type}")
    return 2 if movement_type == "TRANSFER" else 1


def risk_score(reason: str, quantity: Decimal, unit_cost: Decimal) -> Decimal:
    if quantity < 0 or unit_cost < 0:
        raise ValueError("risk inputs must be non-negative")
    rule = REASON_RULES.get(reason)
    if rule is None:
        raise ValueError(f"unknown reason {reason}")
    return (quantity * unit_cost * rule.value_multiplier).quantize(Decimal("0.01"))
