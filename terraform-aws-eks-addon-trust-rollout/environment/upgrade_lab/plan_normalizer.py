"""Parser and normalizer for Terraform show -json execution plans."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def parse_assume_subjects(policy_doc: Any) -> List[str]:
    """Extract IAM assume-role subjects from policy document string or dict."""
    subjects: List[str] = []
    if policy_doc is None:
        return subjects
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(policy_doc)
        except json.JSONDecodeError:
            subjects.extend(re.findall(r"system:serviceaccount:[^\s\"'\\]+", policy_doc))
            if "system:nodes" in policy_doc:
                subjects.append("system:nodes")
            return subjects

    statements = policy_doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        cond = stmt.get("Condition") or {}
        for block in cond.values():
            if not isinstance(block, dict):
                continue
            for key, val in block.items():
                if not str(key).endswith(":sub") and key != "sub":
                    continue
                if isinstance(val, list):
                    subjects.extend(str(v) for v in val)
                else:
                    subjects.append(str(val))
    return subjects


def extract_policy_actions(policy_doc: Any) -> List[str]:
    """Extract IAM policy action strings from policy document."""
    actions: List[str] = []
    if policy_doc is None:
        return actions
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(policy_doc)
        except json.JSONDecodeError:
            return actions

    statements = policy_doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        act = stmt.get("Action")
        if isinstance(act, list):
            actions.extend(str(a) for a in act)
        elif act is not None:
            actions.append(str(act))
        res = stmt.get("Resource")
        if res == "*" and act == "*":
            actions.append("*")
    return actions


def normalize_terraform_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Extract add-ons, IRSA roles, node groups, and regulated placement from plan."""
    changes = plan.get("resource_changes") or []
    addons: Dict[str, Dict[str, Any]] = {}
    roles: Dict[str, Dict[str, Any]] = {}
    role_policies: Dict[str, List[str]] = {}
    node_groups: Dict[str, Dict[str, Any]] = {}
    regulated: Dict[str, Any] = {"capacity_types": [], "name": None, "private_only": None}
    protected_actions: List[Dict[str, Any]] = []

    for rc in changes:
        rtype = rc.get("type")
        change = rc.get("change") or {}
        after = change.get("after") or {}
        actions = list(change.get("actions") or [])
        tags = after.get("tags") or after.get("tags_all") or {}
        if not isinstance(tags, dict):
            tags = {}

        if tags.get("UpgradeProtected") == "true" and ("delete" in actions or "replace" in actions):
            protected_actions.append(
                {"address": rc.get("address"), "actions": actions, "type": rtype}
            )

        if rtype == "aws_eks_addon":
            name = after.get("addon_name") or tags.get("AddonName")
            if name:
                addons[name] = {
                    "addon_name": name,
                    "addon_version": after.get("addon_version"),
                    "resolve_conflicts_on_update": after.get("resolve_conflicts_on_update"),
                    "service_account_role_arn": after.get("service_account_role_arn"),
                    "tags": dict(tags),
                    "actions": actions,
                    "address": rc.get("address"),
                }
        elif rtype == "aws_iam_role":
            trust_key = tags.get("AddonTrust") or tags.get("Name") or after.get("name")
            subjects = parse_assume_subjects(after.get("assume_role_policy"))
            inline_actions: List[str] = []
            for pol in after.get("inline_policy") or []:
                if isinstance(pol, dict):
                    inline_actions.extend(extract_policy_actions(pol.get("policy")))
            roles[str(trust_key)] = {
                "name": after.get("name"),
                "subjects": subjects,
                "tags": dict(tags),
                "actions": actions,
                "address": rc.get("address"),
                "assume_role_policy": after.get("assume_role_policy"),
                "policy_actions": list(dict.fromkeys(inline_actions)),
            }
        elif rtype == "aws_iam_role_policy":
            trust_key = tags.get("AddonTrust") or after.get("name") or rc.get("name")
            acts = extract_policy_actions(after.get("policy"))
            role_policies.setdefault(str(trust_key), []).extend(acts)
            role_name = tags.get("RoleName")
            if role_name:
                role_policies.setdefault(str(role_name), []).extend(acts)
        elif rtype == "aws_eks_node_group":
            ng_name = after.get("node_group_name") or tags.get("NodePool")
            taints = after.get("taint") or after.get("taints") or []
            if isinstance(taints, dict):
                taints = list(taints.values()) if taints else []
            labels = after.get("labels") or {}
            node_groups[str(ng_name)] = {
                "node_group_name": ng_name,
                "labels": dict(labels),
                "taints": taints,
                "tags": dict(tags),
                "actions": actions,
                "address": rc.get("address"),
                "subnet_ids": list(after.get("subnet_ids") or []),
            }
        elif rtype == "aws_eks_cluster":
            if tags.get("UpgradeProtected") == "true" and ("delete" in actions or "replace" in actions):
                protected_actions.append(
                    {"address": rc.get("address"), "actions": actions, "type": rtype}
                )
        elif rtype == "aws_ssm_parameter":
            if tags.get("ControllerAddon"):
                name = tags["ControllerAddon"]
                version = tags.get("AddonVersion") or after.get("value")
                addons[name] = {
                    "addon_name": name,
                    "addon_version": version,
                    "resolve_conflicts_on_update": tags.get("ResolveConflicts") or "PRESERVE",
                    "service_account_role_arn": tags.get("ServiceAccountRoleArn"),
                    "tags": dict(tags),
                    "actions": actions,
                    "address": rc.get("address"),
                }
            if tags.get("RegulatedNodePool") == "true" or tags.get("Component") == "regulated-nodepool":
                capacity = tags.get("CapacityTypes") or ""
                if isinstance(capacity, str):
                    regulated["capacity_types"] = [
                        c.strip() for c in capacity.split(",") if c.strip()
                    ]
                regulated["name"] = tags.get("NodePoolName")
                priv = tags.get("PrivateSubnetsOnly")
                if priv is not None:
                    regulated["private_only"] = str(priv).lower() in {"true", "1", "yes"}

    for key, role in roles.items():
        trust = role["tags"].get("AddonTrust") or key
        merged = list(role.get("policy_actions") or [])
        merged.extend(role_policies.get(str(trust), []))
        merged.extend(role_policies.get(str(role.get("name")), []))
        merged.extend(role_policies.get(key, []))
        role["policy_actions"] = list(dict.fromkeys(merged))

    return {
        "addons": addons,
        "roles": roles,
        "node_groups": node_groups,
        "regulated": regulated,
        "protected_actions": protected_actions,
    }
