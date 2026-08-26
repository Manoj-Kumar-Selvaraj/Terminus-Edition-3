"""Validation engine for normalized Terraform plans against upgrade policies."""
from __future__ import annotations

from typing import Any, Dict, List


def validate_plan_policies(
    graph: Dict[str, Any],
    matrix: Dict[str, Any],
    trust: Dict[str, Any],
    defaults: Dict[str, Any],
    regulated_policy: Dict[str, Any],
    snapshot: Dict[str, Any],
) -> List[str]:
    """Validate normalized plan graph against system upgrade policies."""
    errors: List[str] = []
    required_subjects = trust.get("required_subjects") or {}
    role_names = trust.get("role_names") or {}
    forbidden_subjects = set(trust.get("forbidden_subjects") or [])
    addons_meta = matrix.get("addons") or {}

    # 1. Add-on version and conflict resolution checks
    for name, meta in addons_meta.items():
        planned = graph["addons"].get(name)
        if not planned:
            errors.append(f"missing addon {name}")
            continue
        if planned.get("addon_version") != meta.get("target"):
            errors.append(f"{name}: version mismatch")
        if meta.get("kind") == "eks_addon":
            if planned.get("resolve_conflicts_on_update") != defaults.get("resolve_conflicts_on_update"):
                errors.append(f"{name}: resolve_conflicts must be PRESERVE")

    # 2. IRSA trust roles and single-subject binding
    roles_by_trust: Dict[str, Dict[str, Any]] = {}
    for _key, role in graph["roles"].items():
        trust_key = role["tags"].get("AddonTrust")
        if trust_key:
            roles_by_trust[trust_key] = role
        for tk, rname in role_names.items():
            if role.get("name") == rname:
                roles_by_trust[tk] = role

    for trust_key, subject in required_subjects.items():
        role = roles_by_trust.get(trust_key)
        if not role:
            errors.append(f"missing IRSA role for {trust_key}")
            continue
        subjects = set(role.get("subjects") or [])
        if subject not in subjects:
            errors.append(f"{trust_key}: IRSA subject mismatch")
        if subjects & forbidden_subjects:
            errors.append(f"{trust_key}: forbidden IRSA subject")
        if len(subjects) != 1:
            errors.append(f"{trust_key}: IRSA must trust exactly one subject")
        expected_name = role_names.get(trust_key)
        if expected_name and role.get("name") != expected_name:
            errors.append(f"{trust_key}: role name mismatch")

        # Wildcard / overly broad action check
        for act in role.get("policy_actions") or []:
            if act in (defaults.get("forbidden_policy_actions") or []):
                errors.append(f"{trust_key}: forbidden policy action {act}")
            if act.endswith(":*") and trust_key == "ebs_csi":
                errors.append(f"{trust_key}: policy too broad")

    # 3. System node group taints and labels
    system = graph["node_groups"].get("system")
    if not system:
        errors.append("missing system node group")
    else:
        taint_cfg = defaults.get("system_taint") or {}
        found = False
        for t in system.get("taints") or []:
            if not isinstance(t, dict):
                continue
            if (
                t.get("key") == taint_cfg.get("key")
                and str(t.get("value")) == str(taint_cfg.get("value"))
                and str(t.get("effect")).upper().replace("-", "_")
                in {
                    str(taint_cfg.get("effect")).upper().replace("-", "_"),
                    "NO_SCHEDULE",
                    "NOSCHEDULE",
                }
            ):
                found = True
        if not found:
            errors.append("system node group missing CriticalAddonsOnly taint")
        labels = system.get("labels") or {}
        if labels.get("nodepool") != "system":
            errors.append("system node group label mismatch")
        if system["tags"].get("UpgradeProtected") != "true":
            errors.append("system node group must be UpgradeProtected")

    for pool in ("apps", "batch"):
        ng = graph["node_groups"].get(pool)
        if not ng:
            errors.append(f"missing {pool} node group")
            continue
        if ng["tags"].get("UpgradeProtected") != "true":
            errors.append(f"{pool} node group must be UpgradeProtected")

    # 4. Regulated workload placement
    reg = graph.get("regulated") or {}
    expected_pool = (regulated_policy.get("nodepool") or {}).get("name")
    expected_caps = set((regulated_policy.get("nodepool") or {}).get("capacity_types") or [])
    if reg.get("name") != expected_pool:
        errors.append("regulated nodepool name mismatch")
    caps = set(reg.get("capacity_types") or [])
    if caps != expected_caps:
        errors.append("regulated capacity types must be on-demand only")
    if "spot" in {c.lower() for c in caps}:
        errors.append("regulated capacity must not include spot")
    if reg.get("private_only") is not True:
        errors.append("regulated nodepool must be private-subnet only")

    # 5. Protected resources
    for item in graph.get("protected_actions") or []:
        errors.append(
            f"protected resource {item.get('address')} must not be deleted or replaced"
        )

    if snapshot.get("endpoint_public") is True:
        errors.append("cluster snapshot public endpoint unexpected")

    return errors
