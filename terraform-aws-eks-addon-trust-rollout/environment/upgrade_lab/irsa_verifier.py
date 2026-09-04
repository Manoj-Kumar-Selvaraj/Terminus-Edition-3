"""IRSA trust policy, subject fence, and cross-service trust verifier."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


_SUBJECT_RE = re.compile(r"^system:serviceaccount:([^:]+):([^:]+)$")


def parse_service_account_subject(subject: str) -> Optional[Tuple[str, str]]:
    """Parse system:serviceaccount:ns:name into (namespace, name)."""
    match = _SUBJECT_RE.match(str(subject or ""))
    if not match:
        return None
    return match.group(1), match.group(2)


def build_role_arn_index(
    graph_roles: Dict[str, Any],
    account_id: str,
) -> Dict[str, str]:
    """Map AddonTrust keys to concrete role ARNs from the plan graph."""
    role_arns: Dict[str, str] = {}
    for _k, role in graph_roles.items():
        if not isinstance(role, dict):
            continue
        tags = role.get("tags") or {}
        tk = tags.get("AddonTrust")
        name = role.get("name")
        if tk and name:
            role_arns[str(tk)] = f"arn:aws:iam::{account_id}:role/{name}"
        # Secondary index by role name for annotation cross-checks.
        if name and str(name) not in role_arns:
            role_arns[str(name)] = f"arn:aws:iam::{account_id}:role/{name}"
    return role_arns


def index_service_accounts(
    service_accounts: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(s.get("namespace") or "default"), str(s.get("name") or "")): s
        for s in service_accounts
        if isinstance(s, dict)
    }


def validate_binding(
    trust_key: str,
    subject: str,
    sa: Optional[Dict[str, Any]],
    expected_arn: str,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Validate one IRSA binding annotation against the expected role ARN."""
    errors: List[str] = []
    parsed = parse_service_account_subject(subject)
    if parsed is None:
        errors.append(f"IRSA subject malformed for {trust_key}: {subject}")
        return (
            {"subject": subject, "ok": False, "role_arn": expected_arn},
            False,
            errors,
        )

    ok = bool(sa and sa.get("role_arn") == expected_arn and expected_arn)
    if not expected_arn:
        errors.append(f"IRSA role ARN missing for {trust_key}")
        ok = False
    elif sa is None:
        ns, name = parsed
        errors.append(f"IRSA service account missing for {trust_key} ({ns}/{name})")
        ok = False
    elif sa.get("role_arn") != expected_arn:
        errors.append(
            f"IRSA binding failed for {trust_key} (subject: {subject})"
        )
        ok = False

    return (
        {"subject": subject, "ok": ok, "role_arn": expected_arn},
        ok,
        errors,
    )


def audit_cross_service_isolation(
    bindings: Dict[str, Any],
    required_count: int,
) -> Tuple[bool, List[str]]:
    """Deny shared role ARNs across distinct add-on trust keys."""
    errors: List[str] = []
    arns = [v.get("role_arn") for v in bindings.values() if v.get("role_arn")]
    unique = set(arns)
    denied = len(arns) == len(unique) == required_count and required_count > 0
    if not denied:
        errors.append("Cross-service trust violation: shared role ARN detected")
        # Identify colliding ARNs for operator diagnostics (not graded fields).
        seen: Dict[str, str] = {}
        for key, meta in bindings.items():
            arn = meta.get("role_arn")
            if not arn:
                continue
            prior = seen.get(arn)
            if prior and prior != key:
                errors.append(f"shared ARN {arn} between {prior} and {key}")
            seen[arn] = key
    return denied, errors


def verify_irsa_bindings(
    graph_roles: Dict[str, Any],
    service_accounts: List[Dict[str, Any]],
    trust_config: Dict[str, Any],
    defaults: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Verify service account IRSA annotations match exact role ARNs and enforce cross-service denial."""
    required_subjects = trust_config.get("required_subjects") or {}
    account_id = str(defaults.get("account_id", "123456789012"))

    role_arns = build_role_arn_index(graph_roles, account_id)
    sa_index = index_service_accounts(service_accounts)

    bindings: Dict[str, Any] = {}
    all_ok = True
    errors: List[str] = []

    for trust_key, subject in required_subjects.items():
        parsed = parse_service_account_subject(str(subject))
        sa = None
        if parsed is not None:
            sa = sa_index.get(parsed)
        expected_arn = role_arns.get(str(trust_key), "")
        # Prefer AddonTrust-keyed ARN; role_arns also has name keys.
        if not expected_arn:
            role_names = trust_config.get("role_names") or {}
            rname = role_names.get(trust_key)
            if rname:
                expected_arn = role_arns.get(str(rname), "")
                if not expected_arn and rname:
                    expected_arn = f"arn:aws:iam::{account_id}:role/{rname}"

        binding, ok, errs = validate_binding(str(trust_key), str(subject), sa, expected_arn)
        bindings[str(trust_key)] = binding
        if not ok:
            all_ok = False
            errors.extend(errs)

    cross_ok, cross_errs = audit_cross_service_isolation(
        bindings, len(required_subjects)
    )
    if not cross_ok:
        all_ok = False
        errors.extend(cross_errs)

    # Return cross_service_denied semantics: True means isolation held.
    return bindings, cross_ok and all_ok, list(dict.fromkeys(errors))
