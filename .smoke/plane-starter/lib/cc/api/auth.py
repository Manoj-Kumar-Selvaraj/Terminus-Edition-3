"""Caller identity carried by request headers.

Headers state who is calling, whether they asserted MFA, and the address the
request came from. Nothing here decides access: the evaluator does that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cc.errors import ValidationException
from cc.home import principal
from cc.iam.context import parse_ip, parse_mfa

HEADER_PRINCIPAL = "x-cc-principal"
HEADER_MFA = "x-cc-mfa"
HEADER_SOURCE_IP = "x-cc-source-ip"


@dataclass(frozen=True)
class Caller:
    """Identity and request context asserted by one HTTP caller."""

    principal: str
    mfa: bool | None
    source_ip: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"principal": self.principal, "mfa": self.mfa, "source_ip": self.source_ip}


def normalize_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    """Lowercase header names so callers may use any capitalization."""
    if not headers:
        return {}
    return {str(key).lower(): str(value) for key, value in headers.items()}


def caller_from(headers: Mapping[str, Any] | None) -> Caller:
    """Read the calling identity from request headers."""
    values = normalize_headers(headers)
    name = (values.get(HEADER_PRINCIPAL) or "").strip()
    if not name or principal(name) is None:
        raise ValidationException(
            "MISSING_PRINCIPAL", f"{HEADER_PRINCIPAL} header is missing or unusable"
        )
    return Caller(
        principal=name,
        mfa=parse_mfa(values.get(HEADER_MFA)),
        source_ip=parse_ip(values.get(HEADER_SOURCE_IP)),
    )


def optional_caller(headers: Mapping[str, Any] | None) -> Caller | None:
    """Caller identity when present, for routes that serve anonymous reads."""
    values = normalize_headers(headers)
    if not (values.get(HEADER_PRINCIPAL) or "").strip():
        return None
    return caller_from(headers)
