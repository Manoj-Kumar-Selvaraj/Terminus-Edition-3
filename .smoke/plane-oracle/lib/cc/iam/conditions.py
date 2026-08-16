"""Condition-block evaluation for policy statements.

A statement's Condition maps an operator name to a block of context keys and
expected values. Every operator in a statement must hold for the statement to
apply, and every key inside one operator block must hold as well.
"""

from __future__ import annotations

from typing import Any

from cc.util import as_bool, as_list, glob_match, ip_in_cidr

SUPPORTED_OPERATORS = (
    "StringEquals",
    "StringNotEquals",
    "StringLike",
    "Bool",
    "IpAddress",
    "NotIpAddress",
)


class ConditionOutcome:
    """Result of one operator block, carrying the key that decided it."""

    def __init__(self, satisfied: bool, operator: str = "", key: str = "") -> None:
        self.satisfied = satisfied
        self.operator = operator
        self.key = key

    def __bool__(self) -> bool:
        return self.satisfied


def _string_equals(actual: Any, expected: Any) -> bool:
    options = [str(item) for item in as_list(expected)]
    return str(actual) in options


def _string_not_equals(actual: Any, expected: Any) -> bool:
    options = [str(item) for item in as_list(expected)]
    return str(actual) not in options


def _string_like(actual: Any, expected: Any) -> bool:
    patterns = [str(item) for item in as_list(expected)]
    return any(glob_match(pattern, str(actual)) for pattern in patterns)


def _bool_operator(actual: Any, expected: Any) -> bool:
    return as_bool(actual) is as_bool(expected)


def _ip_address(actual: Any, expected: Any) -> bool:
    return cidr_hit(str(actual), expected)


def _not_ip_address(actual: Any, expected: Any) -> bool:
    return not cidr_hit(str(actual), expected)


OPERATORS = {
    "StringEquals": _string_equals,
    "StringNotEquals": _string_not_equals,
    "StringLike": _string_like,
    "Bool": _bool_operator,
    "IpAddress": _ip_address,
    "NotIpAddress": _not_ip_address,
}


def evaluate_key(operator: str, actual: Any, expected: Any, present: bool) -> bool:
    """Evaluate one context key inside one operator block.

    A key the caller did not supply is absent, and an absent key never
    satisfies the operator that names it.
    """
    if not present:
        return False
    handler = OPERATORS.get(operator)
    if handler is None:
        return False
    return handler(actual, expected)


def evaluate_block(operator: str, block: Any, context: dict[str, Any]) -> ConditionOutcome:
    """Evaluate every key of one operator block against the request context."""
    if not isinstance(block, dict):
        return ConditionOutcome(False, operator)
    if operator not in OPERATORS:
        return ConditionOutcome(False, operator)
    for key, expected in block.items():
        present = key in context
        if not evaluate_key(operator, context.get(key), expected, present):
            return ConditionOutcome(False, operator, key)
    return ConditionOutcome(True, operator)


def evaluate(condition: dict[str, Any] | None, context: dict[str, Any]) -> ConditionOutcome:
    """Evaluate a whole Condition block; an empty condition always holds."""
    if not condition:
        return ConditionOutcome(True)
    for operator, block in condition.items():
        outcome = evaluate_block(operator, block, context)
        if not outcome.satisfied:
            return outcome
    return ConditionOutcome(True)


def describe(condition: dict[str, Any] | None) -> list[str]:
    """Flatten a condition block into operator/key labels for diagnostics."""
    if not condition:
        return []
    labels: list[str] = []
    for operator, block in sorted(condition.items()):
        if isinstance(block, dict):
            labels.extend(f"{operator}:{key}" for key in sorted(block))
        else:
            labels.append(operator)
    return labels


def cidr_hit(address: str, allowed: Any) -> bool:
    """True when address is inside any of the supplied CIDR blocks."""
    return any(ip_in_cidr(address, str(block)) for block in as_list(allowed))
