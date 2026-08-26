"""IRSA trust policy, subject fence, and cross-service trust verifier."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def verify_irsa_bindings(
    graph_roles: Dict[str, Any],
    service_accounts: List[Dict[str, Any]],
    trust_config: Dict[str, Any],
    defaults: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Verify service account IRSA annotations match exact role ARNs and enforce cross-service denial."""
    required_subjects = trust_config.get("required_subjects") or {}
    account_id = defaults.get("account_id", "123456789012")

    # Build role ARN map from plan
    role_arns: Dict[str, str] = {}
    for _k, role in graph_roles.items():
        tk = role.get("tags", {}).get("AddonTrust")
        if tk and role.get("name"):
            role_arns[tk] = f"arn:aws:iam::{account_id}:role/{role['name']}"

    sa_index = {
        (s["namespace"], s["name"]): s for s in service_accounts
    }

    bindings: Dict[str, Any] = {}
    all_ok = True
    errors: List[str] = []

    for trust_key, subject in required_subjects.items():
        parts = subject.split(":")
        ns, name = parts[2], parts[3]
        sa = sa_index.get((ns, name))
        expected_arn = role_arns.get(trust_key, "")
        ok = bool(sa and sa.get("role_arn") == expected_arn and expected_arn)
        bindings[trust_key] = {
            "subject": subject,
            "ok": ok,
            "role_arn": expected_arn,
        }
        if not ok:
            all_ok = False
            errors.append(f"IRSA binding failed for {trust_key} (subject: {subject})")

    # Audit cross-service trust: every binding must have a unique non-empty role_arn
    arns = [v["role_arn"] for v in bindings.values() if v.get("role_arn")]
    cross_service_denied = (
        len(arns) == len(set(arns)) == len(required_subjects)
    )

    if not cross_service_denied:
        all_ok = False
        errors.append("Cross-service trust violation: shared role ARN detected")

    return bindings, cross_service_denied and all_ok, errors
