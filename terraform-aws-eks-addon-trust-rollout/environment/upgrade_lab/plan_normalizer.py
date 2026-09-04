"""Parser and normalizer for Terraform show -json execution plans."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


_SUB_PATTERN = re.compile(r"system:serviceaccount:[^\s\"'\\]+")
_EFFECT_ALIASES = {
    "NO_SCHEDULE": "NO_SCHEDULE",
    "NOSCHEDULE": "NO_SCHEDULE",
    "NO_EXECUTE": "NO_EXECUTE",
    "NOEXECUTE": "NO_EXECUTE",
    "PREFER_NO_SCHEDULE": "PREFER_NO_SCHEDULE",
    "PREFERNOSCHEDULE": "PREFER_NO_SCHEDULE",
}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    return [value]


def _tags_from(after: Dict[str, Any]) -> Dict[str, Any]:
    tags = after.get("tags") or after.get("tags_all") or {}
    return dict(tags) if isinstance(tags, dict) else {}


def _change_actions(rc: Dict[str, Any]) -> List[str]:
    change = _as_dict(rc.get("change"))
    return [str(a) for a in _as_list(change.get("actions"))]


def _after_block(rc: Dict[str, Any]) -> Dict[str, Any]:
    change = _as_dict(rc.get("change"))
    after = change.get("after")
    if after is None:
        return {}
    return _as_dict(after)


def parse_assume_subjects(policy_doc: Any) -> List[str]:
    """Extract IAM assume-role subjects from policy document string or dict."""
    subjects: List[str] = []
    if policy_doc is None:
        return subjects
    if isinstance(policy_doc, str):
        text = policy_doc.strip()
        try:
            policy_doc = json.loads(text)
        except json.JSONDecodeError:
            subjects.extend(_SUB_PATTERN.findall(text))
            if "system:nodes" in text:
                subjects.append("system:nodes")
            for match in re.findall(r'":\s*"([^"]+)"', text):
                if match.startswith("system:serviceaccount:") or match == "system:nodes":
                    if match not in subjects:
                        subjects.append(match)
            return list(dict.fromkeys(subjects))

    if not isinstance(policy_doc, dict):
        return subjects

    statements = policy_doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        if str(stmt.get("Effect", "Allow")).lower() == "deny":
            continue
        cond = stmt.get("Condition") or {}
        if not isinstance(cond, dict):
            continue
        for block in cond.values():
            if not isinstance(block, dict):
                continue
            for key, val in block.items():
                key_s = str(key)
                if not (key_s.endswith(":sub") or key_s == "sub" or key_s.endswith(":Sub")):
                    continue
                if isinstance(val, list):
                    subjects.extend(str(v) for v in val)
                else:
                    subjects.append(str(val))
    return list(dict.fromkeys(subjects))


def extract_policy_actions(policy_doc: Any) -> List[str]:
    """Extract IAM policy action strings from policy document."""
    actions: List[str] = []
    if policy_doc is None:
        return actions
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(policy_doc)
        except json.JSONDecodeError:
            scraped = re.findall(r'"((?:[a-z0-9]+:)?\*|[a-z0-9]+:[A-Za-z0-9*]+)"', policy_doc)
            return list(dict.fromkeys(scraped))

    if not isinstance(policy_doc, dict):
        return actions

    statements = policy_doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        if str(stmt.get("Effect", "Allow")).lower() == "deny":
            continue
        act = stmt.get("Action")
        if isinstance(act, list):
            actions.extend(str(a) for a in act)
        elif act is not None:
            actions.append(str(act))
        if stmt.get("NotAction") is not None:
            actions.append("*")
        res = stmt.get("Resource")
        if res == "*" and act == "*":
            actions.append("*")
    return list(dict.fromkeys(actions))


def extract_policy_resources(policy_doc: Any) -> List[str]:
    """Extract resource ARNs/patterns from an IAM policy document."""
    resources: List[str] = []
    if policy_doc is None:
        return resources
    doc = policy_doc
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except json.JSONDecodeError:
            return resources
    if not isinstance(doc, dict):
        return resources
    statements = doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        res = stmt.get("Resource")
        if isinstance(res, list):
            resources.extend(str(r) for r in res)
        elif res is not None:
            resources.append(str(res))
    return list(dict.fromkeys(resources))


def normalize_taint_entry(raw: Any) -> Optional[Dict[str, str]]:
    """Normalize a Terraform taint object into key/value/effect."""
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    if not key:
        return None
    effect_raw = str(raw.get("effect") or "").upper().replace("-", "_")
    effect = _EFFECT_ALIASES.get(effect_raw, effect_raw)
    return {
        "key": str(key),
        "value": str(raw.get("value") if raw.get("value") is not None else ""),
        "effect": effect,
    }


def normalize_node_group_taints(after: Dict[str, Any]) -> List[Dict[str, str]]:
    """Collect taints from taint / taints fields in either list or map form."""
    collected: List[Dict[str, str]] = []
    for field in ("taint", "taints"):
        for item in _as_list(after.get(field)):
            normalized = normalize_taint_entry(item)
            if normalized:
                collected.append(normalized)
    seen = set()
    unique: List[Dict[str, str]] = []
    for t in collected:
        sig = (t["key"], t["value"], t["effect"])
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(t)
    return unique


def parse_capacity_types(raw: Any) -> List[str]:
    """Parse capacity type lists from tags or structured values."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            loaded = json.loads(text)
            if isinstance(loaded, list):
                return [str(x).strip() for x in loaded if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_bool_tag(raw: Any) -> Optional[bool]:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def merge_role_policy_actions(
    roles: Dict[str, Dict[str, Any]],
    role_policies: Dict[str, List[str]],
) -> None:
    """Merge inline role actions with standalone aws_iam_role_policy attachments."""
    for key, role in roles.items():
        trust = role.get("tags", {}).get("AddonTrust") or key
        merged: List[str] = list(role.get("policy_actions") or [])
        for lookup in (str(trust), str(role.get("name") or ""), key):
            if not lookup:
                continue
            merged.extend(role_policies.get(lookup, []))
        address = str(role.get("address") or "")
        if address:
            merged.extend(role_policies.get(address, []))
        role["policy_actions"] = list(dict.fromkeys(merged))


def record_protected_action(
    protected_actions: List[Dict[str, Any]],
    rc: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    if tags.get("UpgradeProtected") != "true":
        return
    if "delete" not in actions and "replace" not in actions:
        return
    protected_actions.append(
        {
            "address": rc.get("address"),
            "actions": list(actions),
            "type": rc.get("type"),
            "name": rc.get("name"),
        }
    )


def ingest_eks_addon(
    addons: Dict[str, Dict[str, Any]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    name = after.get("addon_name") or tags.get("AddonName")
    if not name:
        return
    addons[str(name)] = {
        "addon_name": str(name),
        "addon_version": after.get("addon_version"),
        "resolve_conflicts_on_update": after.get("resolve_conflicts_on_update"),
        "resolve_conflicts": after.get("resolve_conflicts"),
        "service_account_role_arn": after.get("service_account_role_arn"),
        "configuration_values": after.get("configuration_values"),
        "tags": dict(tags),
        "actions": list(actions),
        "address": rc.get("address"),
    }


def ingest_iam_role(
    roles: Dict[str, Dict[str, Any]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    trust_key = tags.get("AddonTrust") or tags.get("Name") or after.get("name") or rc.get("name")
    subjects = parse_assume_subjects(after.get("assume_role_policy"))
    inline_actions: List[str] = []
    inline_resources: List[str] = []
    for pol in _as_list(after.get("inline_policy")):
        if not isinstance(pol, dict):
            continue
        inline_actions.extend(extract_policy_actions(pol.get("policy")))
        inline_resources.extend(extract_policy_resources(pol.get("policy")))
    roles[str(trust_key)] = {
        "name": after.get("name"),
        "subjects": subjects,
        "tags": dict(tags),
        "actions": list(actions),
        "address": rc.get("address"),
        "assume_role_policy": after.get("assume_role_policy"),
        "policy_actions": list(dict.fromkeys(inline_actions)),
        "policy_resources": list(dict.fromkeys(inline_resources)),
        "max_session_duration": after.get("max_session_duration"),
    }


def ingest_iam_role_policy(
    role_policies: Dict[str, List[str]],
    role_policy_resources: Dict[str, List[str]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
) -> None:
    trust_key = tags.get("AddonTrust") or after.get("name") or rc.get("name")
    acts = extract_policy_actions(after.get("policy"))
    resources = extract_policy_resources(after.get("policy"))
    role_policies.setdefault(str(trust_key), []).extend(acts)
    role_policy_resources.setdefault(str(trust_key), []).extend(resources)
    role_name = tags.get("RoleName") or after.get("role")
    if role_name:
        role_policies.setdefault(str(role_name), []).extend(acts)
        role_policy_resources.setdefault(str(role_name), []).extend(resources)
    role_address = tags.get("RoleAddress")
    if role_address:
        role_policies.setdefault(str(role_address), []).extend(acts)


def ingest_iam_role_policy_attachment(
    attachments: Dict[str, List[str]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
) -> None:
    trust_key = tags.get("AddonTrust") or after.get("role") or rc.get("name")
    policy_arn = after.get("policy_arn")
    if trust_key and policy_arn:
        attachments.setdefault(str(trust_key), []).append(str(policy_arn))


def ingest_node_group(
    node_groups: Dict[str, Dict[str, Any]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    ng_name = after.get("node_group_name") or tags.get("NodePool") or rc.get("name")
    labels = after.get("labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    scaling = after.get("scaling_config")
    scaling_list = _as_list(scaling)
    scaling_cfg = (
        scaling_list[0] if scaling_list and isinstance(scaling_list[0], dict) else _as_dict(scaling)
    )
    node_groups[str(ng_name)] = {
        "node_group_name": ng_name,
        "labels": dict(labels),
        "taints": normalize_node_group_taints(after),
        "tags": dict(tags),
        "actions": list(actions),
        "address": rc.get("address"),
        "subnet_ids": [str(s) for s in _as_list(after.get("subnet_ids"))],
        "instance_types": [str(i) for i in _as_list(after.get("instance_types"))],
        "capacity_type": after.get("capacity_type"),
        "ami_type": after.get("ami_type"),
        "scaling_config": {
            "desired_size": scaling_cfg.get("desired_size"),
            "max_size": scaling_cfg.get("max_size"),
            "min_size": scaling_cfg.get("min_size"),
        },
    }


def ingest_ssm_parameter(
    addons: Dict[str, Dict[str, Any]],
    regulated: Dict[str, Any],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    if tags.get("ControllerAddon"):
        name = str(tags["ControllerAddon"])
        version = tags.get("AddonVersion") or after.get("value")
        addons[name] = {
            "addon_name": name,
            "addon_version": version,
            "resolve_conflicts_on_update": tags.get("ResolveConflicts") or "PRESERVE",
            "service_account_role_arn": tags.get("ServiceAccountRoleArn"),
            "tags": dict(tags),
            "actions": list(actions),
            "address": rc.get("address"),
            "source": "ssm_parameter",
        }
    if tags.get("RegulatedNodePool") == "true" or tags.get("Component") == "regulated-nodepool":
        capacity = tags.get("CapacityTypes")
        if capacity is None and after.get("value"):
            try:
                parsed = json.loads(str(after.get("value")))
                if isinstance(parsed, dict):
                    capacity = parsed.get("capacity_types")
                    if regulated.get("private_only") is None and "private_only" in parsed:
                        regulated["private_only"] = bool(parsed.get("private_only"))
            except (json.JSONDecodeError, TypeError):
                capacity = None
        regulated["capacity_types"] = parse_capacity_types(capacity)
        regulated["name"] = tags.get("NodePoolName") or regulated.get("name")
        priv = parse_bool_tag(tags.get("PrivateSubnetsOnly"))
        if priv is not None:
            regulated["private_only"] = priv
        discovery = tags.get("DiscoveryTagKey") or tags.get("DiscoveryTag")
        if discovery:
            regulated["discovery_tag_key"] = discovery


def ingest_launch_template(
    launch_templates: Dict[str, Dict[str, Any]],
    rc: Dict[str, Any],
    after: Dict[str, Any],
    tags: Dict[str, Any],
    actions: List[str],
) -> None:
    name = after.get("name") or tags.get("Name") or rc.get("name")
    launch_templates[str(name)] = {
        "name": name,
        "tags": dict(tags),
        "actions": list(actions),
        "address": rc.get("address"),
        "image_id": after.get("image_id"),
        "instance_type": after.get("instance_type"),
    }


def normalize_terraform_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Extract add-ons, IRSA roles, node groups, and regulated placement from plan."""
    changes = plan.get("resource_changes") or []
    addons: Dict[str, Dict[str, Any]] = {}
    roles: Dict[str, Dict[str, Any]] = {}
    role_policies: Dict[str, List[str]] = {}
    role_policy_resources: Dict[str, List[str]] = {}
    policy_attachments: Dict[str, List[str]] = {}
    node_groups: Dict[str, Dict[str, Any]] = {}
    launch_templates: Dict[str, Dict[str, Any]] = {}
    regulated: Dict[str, Any] = {
        "capacity_types": [],
        "name": None,
        "private_only": None,
        "discovery_tag_key": None,
    }
    protected_actions: List[Dict[str, Any]] = []
    ignored_types: List[str] = []

    for rc in changes:
        if not isinstance(rc, dict):
            continue
        rtype = rc.get("type")
        after = _after_block(rc)
        actions = _change_actions(rc)
        tags = _tags_from(after)
        record_protected_action(protected_actions, rc, tags, actions)

        if rtype == "aws_eks_addon":
            ingest_eks_addon(addons, rc, after, tags, actions)
        elif rtype == "aws_iam_role":
            ingest_iam_role(roles, rc, after, tags, actions)
        elif rtype == "aws_iam_role_policy":
            ingest_iam_role_policy(role_policies, role_policy_resources, rc, after, tags)
        elif rtype == "aws_iam_role_policy_attachment":
            ingest_iam_role_policy_attachment(policy_attachments, rc, after, tags)
        elif rtype == "aws_eks_node_group":
            ingest_node_group(node_groups, rc, after, tags, actions)
        elif rtype == "aws_eks_cluster":
            pass
        elif rtype == "aws_ssm_parameter":
            ingest_ssm_parameter(addons, regulated, rc, after, tags, actions)
        elif rtype in {"aws_launch_template", "aws_eks_access_entry"}:
            ingest_launch_template(launch_templates, rc, after, tags, actions)
        elif rtype:
            ignored_types.append(str(rtype))

    merge_role_policy_actions(roles, role_policies)
    for key, role in roles.items():
        trust = role.get("tags", {}).get("AddonTrust") or key
        resources = list(role.get("policy_resources") or [])
        resources.extend(role_policy_resources.get(str(trust), []))
        resources.extend(role_policy_resources.get(str(role.get("name") or ""), []))
        role["policy_resources"] = list(dict.fromkeys(resources))
        role["attached_policy_arns"] = list(
            dict.fromkeys(
                policy_attachments.get(str(trust), []) + policy_attachments.get(key, [])
            )
        )

    return {
        "addons": addons,
        "roles": roles,
        "node_groups": node_groups,
        "launch_templates": launch_templates,
        "regulated": regulated,
        "protected_actions": protected_actions,
        "meta": {
            "resource_change_count": len(changes),
            "ignored_type_count": len(ignored_types),
        },
    }


# Alias used by verifier fixture mirror naming.
normalize_plan = normalize_terraform_plan
