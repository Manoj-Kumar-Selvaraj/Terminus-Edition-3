"""Shared helpers: ref naming, wildcard matching, CIDR tests, row ordering."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

REF_PREFIX = "refs/heads/"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def normalize_ref(ref: str) -> str:
    """Expand a caller-supplied branch name into its full ref form."""
    value = (ref or "").strip()
    if not value:
        raise ValueError("empty ref")
    value = value.rstrip("/")
    if value.startswith("refs/"):
        return value
    if value.startswith("heads/"):
        return f"refs/{value}"
    return f"{REF_PREFIX}{value}"


def short_ref(ref: str) -> str:
    """Return the branch name for a full ref, or the input when already short."""
    if ref.startswith(REF_PREFIX):
        return ref[len(REF_PREFIX) :]
    return ref


def is_commit_id(value: str) -> bool:
    """True when the value looks like a full 40 hex character object id."""
    return bool(_SHA_RE.match(value or ""))


def glob_match(pattern: str, value: str) -> bool:
    """Match a value against an IAM-style pattern where ``*`` spans any run."""
    if pattern == value:
        return True
    if "*" not in pattern and "?" not in pattern:
        return False
    expression = []
    for char in pattern:
        if char == "*":
            expression.append(".*")
        elif char == "?":
            expression.append(".")
        else:
            expression.append(re.escape(char))
    return re.fullmatch("".join(expression), value) is not None


def ip_in_cidr(address: str, cidr: str) -> bool:
    """True when address falls inside cidr; malformed input never matches."""
    try:
        host = ipaddress.ip_address(address.strip())
    except ValueError:
        return False
    text = cidr.strip()
    try:
        if "/" in text:
            network = ipaddress.ip_network(text, strict=False)
        else:
            network = ipaddress.ip_network(f"{text}/32", strict=False)
    except ValueError:
        return False
    if host.version != network.version:
        return False
    return host in network


def as_list(value: Any) -> list[Any]:
    """Coerce a scalar-or-list policy field into a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def as_bool(value: Any) -> bool:
    """Interpret JSON and policy truth spellings consistently."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "on"}
    return False


def ordered_row(values: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    """Project a mapping onto an exact key order for journal and log rows."""
    row: dict[str, Any] = {}
    for key in keys:
        if key not in values:
            raise KeyError(f"row is missing contracted key {key!r}")
        row[key] = values[key]
    return row


def json_line(row: Mapping[str, Any]) -> str:
    """Serialize one append-only record, preserving insertion order."""
    return json.dumps(row, separators=(",", ":"), sort_keys=False)


def digest(*parts: str) -> str:
    """Stable sha256 hex digest over pipe-joined parts."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def stamp() -> str:
    """Second-resolution UTC timestamp for non-graded bookkeeping fields."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def unique(items: Iterable[str]) -> list[str]:
    """Stable de-duplication preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
