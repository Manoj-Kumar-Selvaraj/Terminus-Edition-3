"""Request-context assembly.

The caller identity, MFA state, and source address arrive from an operator
surface (CLI flags or HTTP headers). This module turns them into the context
key set a policy condition can inspect, without inventing values that the
caller did not supply.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from cc.errors import ValidationException
from cc.iam.actions import is_ref_scoped, validate_action
from cc.models import RequestContext
from cc.util import normalize_ref


def parse_ip(value: str | None) -> str | None:
    """Validate a caller-supplied source address."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        ipaddress.ip_address(text)
    except ValueError as exc:
        raise ValidationException("BAD_SOURCE_IP", f"invalid source address {text!r}") from exc
    return text


def parse_mfa(value: Any) -> bool | None:
    """Interpret an MFA marker; ``None`` means the caller asserted nothing."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "":
        return None
    if text in {"true", "yes", "1", "on"}:
        return True
    if text in {"false", "no", "0", "off"}:
        return False
    raise ValidationException("BAD_MFA_FLAG", f"invalid MFA marker {value!r}")


def build(
    principal: str,
    action: str,
    repo: str,
    *,
    ref: str | None = None,
    mfa: Any = None,
    source_ip: str | None = None,
) -> RequestContext:
    """Assemble the evaluated request context for one authorization call."""
    if not principal or not str(principal).strip():
        raise ValidationException("MISSING_PRINCIPAL", "no calling principal was supplied")
    validate_action(action)
    if not repo:
        raise ValidationException("MISSING_REPOSITORY", "no repository was supplied")
    full_ref = normalize_ref(ref) if ref else None
    if is_ref_scoped(action) and full_ref is None:
        raise ValidationException("MISSING_REF", f"{action} requires a target ref")
    return RequestContext(
        principal=str(principal).strip(),
        action=action,
        repo=repo,
        ref=full_ref,
        source_ip=parse_ip(source_ip),
        mfa=parse_mfa(mfa),
    )


def context_keys(request: RequestContext) -> dict[str, Any]:
    """Context keys visible to condition operators for this request."""
    return request.keys()
