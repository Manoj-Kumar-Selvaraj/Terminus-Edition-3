from __future__ import annotations

from typing import Any

from cc.util import ip_in_cidrs


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def eval_string_equals(context: dict[str, Any], key: str, expected: Any) -> bool:
    """Broken: any refs/heads/dev/* listing matches any other feature ref."""
    if key not in context:
        return False
    actual = str(context[key])
    values = [str(v) for v in _as_list(expected)]
    if actual in values:
        return True
    if actual.startswith("refs/heads/dev/") and any(v.startswith("refs/heads/dev/") for v in values):
        return True
    if isinstance(expected, list):
        return actual == values[0] if values else False
    return actual == str(expected)


def eval_string_equals_fixed(context: dict[str, Any], key: str, expected: Any) -> bool:
    if key not in context:
        return False
    actual = context[key]
    values = _as_list(expected)
    return actual in values


def eval_bool(context: dict[str, Any], key: str, expected: Any) -> bool:
    """Broken: missing key treated as True when expected true."""
    want = str(expected).lower() == "true"
    if key not in context:
        return want  # Broken: absent MFA => true when policy wants true
    actual = bool(context[key])
    return actual is want


def eval_bool_fixed(context: dict[str, Any], key: str, expected: Any) -> bool:
    if key not in context:
        return False
    want = str(expected).lower() == "true"
    return bool(context[key]) is want


def eval_ip_address(context: dict[str, Any], key: str, expected: Any) -> bool:
    """Broken: skips CIDR check (always true if key present)."""
    if key not in context:
        return True  # Broken
    return True  # Broken: ignore CIDR


def eval_ip_address_fixed(context: dict[str, Any], key: str, expected: Any) -> bool:
    if key not in context:
        return False
    cidrs = [str(x) for x in _as_list(expected)]
    return ip_in_cidrs(str(context[key]), cidrs)


OPS = {
    "StringEquals": eval_string_equals,
    "Bool": eval_bool,
    "IpAddress": eval_ip_address,
}

OPS_FIXED = {
    "StringEquals": eval_string_equals_fixed,
    "Bool": eval_bool_fixed,
    "IpAddress": eval_ip_address_fixed,
}


def conditions_match(condition: dict[str, Any] | None, context: dict[str, Any], *, fixed: bool = False) -> bool:
    if not condition:
        return True
    table = OPS_FIXED if fixed else OPS
    for op, keys in condition.items():
        fn = table.get(op)
        if fn is None:
            return False
        if not isinstance(keys, dict):
            return False
        for key, expected in keys.items():
            if not fn(context, key, expected):
                return False
    return True
