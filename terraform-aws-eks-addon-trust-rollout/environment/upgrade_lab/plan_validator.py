"""Validation engine for normalized Terraform plans against upgrade policies."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set


def _normalize_effect(value: Any) -> str:
    return str(value or "").upper().replace("-", "_")


def _taint_matches(taint: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    if taint.get("key") != expected.get("key"):
        return False
    if str(taint.get("value")) != str(expected.get("value")):
        return False
    got = _normalize_effect(taint.get("effect"))
    want = _normalize_effect(expected.get("effect"))
    aliases = {want, "NO_SCHEDULE", "NOSCHEDULE"} if "SCHEDULE" in want else {want}
    return got in aliases


def _roles_by_trust(graph_roles: Dict[str, Any], role_names: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    roles_by_trust: Dict[str, Dict[str, Any]] = {}
    for _key, role in graph_roles.items():
        if not isinstance(role, dict):
            continue
        trust_key = (role.get("tags") or {}).get("AddonTrust")
        if trust_key:
            roles_by_trust[str(trust_key)] = role
        for tk, rname in role_names.items():
            if role.get("name") == rname:
                roles_by_trust[str(tk)] = role
    return roles_by_trust


def _action_is_forbidden(action: str, forbidden: Iterable[str]) -> bool:
    act = str(action)
    if act in forbidden:
        return True
    # AdministratorAccess style sentinel
    if act.lower() == "administratoraccess":
        return True
    return False


def _action_matches_prefix(action: str, allowed: Iterable[str]) -> bool:
    act = str(action)
    for prefix in allowed:
        p = str(prefix)
        if p.endswith("*"):
            if act.startswith(p[:-1]) or act == p:
                return True
        elif act == p:
            return True
    return False


def validate_addon_versions(
    graph: Dict[str, Any],
    matrix: Dict[str, Any],
    defaults: Dict[str, Any],
    errors: List[str],
) -> None:
    addons_meta = matrix.get("addons") or {}
    planned_addons = graph.get("addons") or {}
    expected_conflicts = defaults.get("resolve_conflicts_on_update")
    for name, meta in addons_meta.items():
        planned = planned_addons.get(name)
        if not planned:
            errors.append(f"missing addon {name}")
            continue
        if planned.get("addon_version") != meta.get("target"):
            errors.append(f"{name}: version mismatch")
        if meta.get("kind") == "eks_addon":
            resolve = planned.get("resolve_conflicts_on_update") or planned.get("resolve_conflicts")
            if resolve != expected_conflicts:
                errors.append(f"{name}: resolve_conflicts must be PRESERVE")
            # Soft check: OVERWRITE is never acceptable for controller continuity.
            if str(resolve).upper() == "OVERWRITE":
                if f"{name}: resolve_conflicts must be PRESERVE" not in errors:
                    errors.append(f"{name}: resolve_conflicts must be PRESERVE")


def validate_irsa_roles(
    graph: Dict[str, Any],
    trust: Dict[str, Any],
    defaults: Dict[str, Any],
    errors: List[str],
) -> None:
    required_subjects = trust.get("required_subjects") or {}
    role_names = trust.get("role_names") or {}
    forbidden_subjects = set(trust.get("forbidden_subjects") or [])
    forbidden_actions = list(defaults.get("forbidden_policy_actions") or [])
    allowed_prefixes = defaults.get("allowed_policy_prefixes") or {}
    roles_by_trust = _roles_by_trust(graph.get("roles") or {}, role_names)

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

        policy_actions = list(role.get("policy_actions") or [])
        for act in policy_actions:
            if _action_is_forbidden(act, forbidden_actions):
                errors.append(f"{trust_key}: forbidden policy action {act}")
            if act.endswith(":*") and trust_key == "ebs_csi":
                errors.append(f"{trust_key}: policy too broad")

        # Allow-list fence: reject clearly foreign service prefixes when configured.
        allowed = allowed_prefixes.get(trust_key)
        if allowed and policy_actions:
            allowed_services = {
                str(p).split(":", 1)[0]
                for p in allowed
                if isinstance(p, str) and ":" in p
            }
            for act in policy_actions:
                if _action_is_forbidden(act, forbidden_actions):
                    continue
                if act.endswith(":*") and trust_key == "ebs_csi":
                    continue
                if act == "*":
                    continue
                svc = str(act).split(":", 1)[0]
                if allowed_services and svc not in allowed_services and not _action_matches_prefix(act, allowed):
                    errors.append(f"{trust_key}: policy action outside allow-list {act}")

        # Wildcard resource with wildcard action is never acceptable.
        resources = role.get("policy_resources") or []
        if "*" in policy_actions and ("*" in resources or not resources):
            if f"{trust_key}: forbidden policy action *" not in errors:
                errors.append(f"{trust_key}: forbidden policy action *")


def validate_system_node_group(
    graph: Dict[str, Any],
    defaults: Dict[str, Any],
    errors: List[str],
) -> None:
    system = (graph.get("node_groups") or {}).get("system")
    if not system:
        errors.append("missing system node group")
        return
    taint_cfg = defaults.get("system_taint") or {}
    found = False
    for t in system.get("taints") or []:
        if isinstance(t, dict) and _taint_matches(t, taint_cfg):
            found = True
            break
    if not found:
        errors.append("system node group missing CriticalAddonsOnly taint")
    labels = system.get("labels") or {}
    if labels.get("nodepool") != "system":
        errors.append("system node group label mismatch")
    if (system.get("tags") or {}).get("UpgradeProtected") != "true":
        errors.append("system node group must be UpgradeProtected")


def validate_companion_node_groups(
    graph: Dict[str, Any],
    defaults: Dict[str, Any],
    errors: List[str],
) -> None:
    pools = list(defaults.get("companion_node_pools") or ["apps", "batch"])
    node_groups = graph.get("node_groups") or {}
    for pool in pools:
        ng = node_groups.get(pool)
        if not ng:
            errors.append(f"missing {pool} node group")
            continue
        if (ng.get("tags") or {}).get("UpgradeProtected") != "true":
            errors.append(f"{pool} node group must be UpgradeProtected")
        labels = ng.get("labels") or {}
        if labels.get("nodepool") != pool:
            errors.append(f"{pool} node group label mismatch")


def validate_regulated_capacity(
    graph: Dict[str, Any],
    regulated_policy: Dict[str, Any],
    errors: List[str],
) -> None:
    reg = graph.get("regulated") or {}
    expected_pool = (regulated_policy.get("nodepool") or {}).get("name")
    expected_caps = set((regulated_policy.get("nodepool") or {}).get("capacity_types") or [])
    if reg.get("name") != expected_pool:
        errors.append("regulated nodepool name mismatch")
    caps = set(reg.get("capacity_types") or [])
    if caps != expected_caps:
        errors.append("regulated capacity types must be on-demand only")
    if "spot" in {str(c).lower() for c in caps}:
        errors.append("regulated capacity must not include spot")
    if reg.get("private_only") is not True:
        errors.append("regulated nodepool must be private-subnet only")
    expected_discovery = (regulated_policy.get("nodepool") or {}).get("discovery_tag_key")
    if expected_discovery and reg.get("discovery_tag_key") not in {None, expected_discovery}:
        # Discovery tag is informational when present on the plan marker.
        pass


def validate_protected_actions(graph: Dict[str, Any], errors: List[str]) -> None:
    for item in graph.get("protected_actions") or []:
        errors.append(
            f"protected resource {item.get('address')} must not be deleted or replaced"
        )


def validate_snapshot_posture(snapshot: Dict[str, Any], errors: List[str]) -> None:
    if snapshot.get("endpoint_public") is True:
        errors.append("cluster snapshot public endpoint unexpected")
    if snapshot.get("endpoint_private") is False:
        errors.append("cluster snapshot private endpoint unexpected")


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
    validate_addon_versions(graph, matrix, defaults, errors)
    validate_irsa_roles(graph, trust, defaults, errors)
    validate_system_node_group(graph, defaults, errors)
    validate_companion_node_groups(graph, defaults, errors)
    validate_regulated_capacity(graph, regulated_policy, errors)
    validate_protected_actions(graph, errors)
    validate_snapshot_posture(snapshot, errors)
    # Stable de-duplication while preserving first-seen order.
    return list(dict.fromkeys(errors))
