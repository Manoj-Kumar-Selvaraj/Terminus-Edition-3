"""Local EKS add-on trust upgrade lab (filesystem + YAML state machine)."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - baked in images
    yaml = None  # type: ignore


def _data_dir() -> Path:
    return Path(os.environ.get("UPGRADE_DATA_DIR", "/app/data"))


def _var_dir() -> Path:
    return Path(os.environ.get("UPGRADE_VAR_DIR", "/app/var/upgrade"))


def _output_dir() -> Path:
    return Path(os.environ.get("UPGRADE_OUTPUT_DIR", "/app/output"))


def _k8s_dir() -> Path:
    return Path(os.environ.get("UPGRADE_K8S_DIR", "/app/k8s"))


def _load(name: str) -> Any:
    return json.loads((_data_dir() / name).read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_digest(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_text(body)


def _parse_assume_subjects(policy_doc: Any) -> list[str]:
    subjects: list[str] = []
    if policy_doc is None:
        return subjects
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(policy_doc)
        except json.JSONDecodeError:
            # Terraform may leave interpolations; scrape string literals.
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


def _policy_actions(policy_doc: Any) -> list[str]:
    actions: list[str] = []
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


def normalize_plan(plan: dict) -> dict:
    """Extract addons, IRSA roles, node groups, and regulated placement from a TF plan."""
    changes = plan.get("resource_changes") or []
    addons: dict[str, dict] = {}
    roles: dict[str, dict] = {}
    role_policies: dict[str, list[str]] = {}
    node_groups: dict[str, dict] = {}
    regulated: dict[str, Any] = {"capacity_types": [], "name": None, "private_only": None}
    protected_actions: list[dict] = []

    for rc in changes:
        rtype = rc.get("type")
        after = (rc.get("change") or {}).get("after") or {}
        actions = list((rc.get("change") or {}).get("actions") or [])
        tags = after.get("tags") or after.get("tags_all") or {}
        if not isinstance(tags, dict):
            tags = {}

        if tags.get("UpgradeProtected") == "true" and (
            "delete" in actions or "replace" in actions
        ):
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
            subjects = _parse_assume_subjects(after.get("assume_role_policy"))
            inline_actions: list[str] = []
            for pol in after.get("inline_policy") or []:
                if isinstance(pol, dict):
                    inline_actions.extend(_policy_actions(pol.get("policy")))
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
            acts = _policy_actions(after.get("policy"))
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
            if tags.get("UpgradeProtected") == "true" and (
                "delete" in actions or "replace" in actions
            ):
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

    # Merge any standalone role policies into roles by trust key / name
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


def upgrade_order(matrix: dict) -> list[str]:
    addons = matrix.get("addons") or {}
    return [name for name, _meta in sorted(addons.items(), key=lambda kv: kv[1].get("order", 0))]


def plan_policy_errors(
    graph: dict,
    matrix: dict,
    trust: dict,
    defaults: dict,
    regulated_policy: dict,
    snapshot: dict,
) -> list[str]:
    errors: list[str] = []
    required_subjects = trust.get("required_subjects") or {}
    role_names = trust.get("role_names") or {}
    forbidden_subjects = set(trust.get("forbidden_subjects") or [])
    addons_meta = matrix.get("addons") or {}

    # Addon versions + resolve conflicts
    for name, meta in addons_meta.items():
        planned = graph["addons"].get(name)
        if not planned:
            errors.append(f"missing addon {name}")
            continue
        if planned.get("addon_version") != meta.get("target"):
            errors.append(f"{name}: version mismatch")
        if meta.get("kind") == "eks_addon":
            if planned.get("resolve_conflicts_on_update") != defaults.get(
                "resolve_conflicts_on_update"
            ):
                errors.append(f"{name}: resolve_conflicts must be PRESERVE")

    # IRSA subjects exact match
    roles_by_trust: dict[str, dict] = {}
    for _key, role in graph["roles"].items():
        trust_key = role["tags"].get("AddonTrust")
        if trust_key:
            roles_by_trust[trust_key] = role
        # also allow lookup by expected role name
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
        # Policy must not be wildcard / admin
        for act in role.get("policy_actions") or []:
            if act in (defaults.get("forbidden_policy_actions") or []):
                errors.append(f"{trust_key}: forbidden policy action {act}")
            if act.endswith(":*") and trust_key == "ebs_csi":
                # ebs must stay narrowly scoped — no service wildcards
                errors.append(f"{trust_key}: policy too broad")

    # System node group taint
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
        labels = ng.get("labels") or {}
        if labels.get("nodepool") != pool:
            errors.append(f"{pool} node group label mismatch")

    # Regulated placement
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

    # Protected delete/replace
    for item in graph.get("protected_actions") or []:
        errors.append(
            f"protected resource {item.get('address')} must not be deleted or replaced"
        )

    # Endpoint posture from snapshot defaults — cluster public must stay false in tags/data
    if snapshot.get("endpoint_public") is True:
        errors.append("cluster snapshot public endpoint unexpected")

    return errors


def _load_yaml_docs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    docs = list(yaml.safe_load_all(text))
    return [d for d in docs if isinstance(d, dict)]


def apply_k8s_manifests(k8s_dir: Path | None = None) -> dict:
    """Load submitted manifests into a simple cluster state dict."""
    root = k8s_dir or _k8s_dir()
    state: dict[str, Any] = {
        "pdbs": [],
        "service_accounts": [],
        "deployments": [],
        "nodepools": [],
        "workloads": [],
    }
    if not root.is_dir():
        return state
    for path in sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")):
        for doc in _load_yaml_docs(path):
            kind = doc.get("kind")
            meta = doc.get("metadata") or {}
            if kind == "PodDisruptionBudget":
                spec = doc.get("spec") or {}
                state["pdbs"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "min_available": spec.get("minAvailable"),
                        "selector": ((spec.get("selector") or {}).get("matchLabels") or {}),
                    }
                )
            elif kind == "ServiceAccount":
                ann = (meta.get("annotations") or {})
                state["service_accounts"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "role_arn": ann.get("eks.amazonaws.com/role-arn", ""),
                    }
                )
            elif kind == "Deployment":
                spec = doc.get("spec") or {}
                template = (spec.get("template") or {}).get("metadata") or {}
                state["deployments"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "replicas": spec.get("replicas", 1),
                        "labels": (template.get("labels") or {}),
                    }
                )
                _maybe_record_regulated(state, kind, meta, spec)
            elif kind == "StatefulSet":
                spec = doc.get("spec") or {}
                _maybe_record_regulated(state, kind, meta, spec)
            elif kind in {"NodePool", "EC2NodeClass"}:
                state["nodepools"].append(doc)
    return state


def _maybe_record_regulated(state: dict, kind: str, meta: dict, spec: dict) -> None:
    labels = meta.get("labels") or {}
    if meta.get("namespace") != "regulated" and labels.get("workload-class") != "regulated":
        return
    template = spec.get("template") or {}
    pod_spec = template.get("spec") or {}
    node_selector = pod_spec.get("nodeSelector") or {}
    state["workloads"].append(
        {
            "name": meta.get("name"),
            "namespace": meta.get("namespace"),
            "nodepool": node_selector.get("nodepool")
            or node_selector.get("karpenter.sh/nodepool"),
            "capacity_type": node_selector.get("karpenter.sh/capacity-type"),
            "replicas": spec.get("replicas", 1),
            "kind": kind,
        }
    )


def _pdb_coverage(state: dict, required: list[dict]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    have = {(p["namespace"], p["name"]): p for p in state.get("pdbs") or []}
    for req in required:
        key = (req["namespace"], req["name"])
        got = have.get(key)
        if not got:
            missing.append(f"missing pdb {req['namespace']}/{req['name']}")
            continue
        if got.get("min_available") != req.get("min_available"):
            missing.append(f"pdb {req['name']} minAvailable mismatch")
    return (not missing), missing


def _resolve_replicas(service: str, pdb: dict | None, deployments: list[dict], defaults: dict) -> int:
    if pdb is not None:
        selector = pdb.get("selector") or {}
        namespace = pdb.get("namespace") or "default"
        for dep in deployments:
            if (dep.get("namespace") or "default") != namespace:
                continue
            labels = dep.get("labels") or {}
            if selector and all(labels.get(k) == v for k, v in selector.items()):
                try:
                    return max(0, int(dep.get("replicas") or 0))
                except (TypeError, ValueError):
                    return 0
            if dep.get("name") == pdb.get("name"):
                try:
                    return max(0, int(dep.get("replicas") or 0))
                except (TypeError, ValueError):
                    return 0
    fallback = (defaults.get("core_service_replicas") or {}).get(service)
    try:
        return max(0, int(fallback or 0))
    except (TypeError, ValueError):
        return 0


def _simulate_drain(
    defaults: dict,
    state: dict,
    required_pdbs: list[dict],
) -> tuple[dict, dict[str, bool], bool]:
    """Mirror environment drain_simulator: PDB floors + replica capacity."""
    drain_node = defaults.get("drain_node")
    core_services = list(defaults.get("core_services") or [])
    availability = {name: False for name in core_services}
    deployments = list(state.get("deployments") or [])
    submitted = {(p.get("namespace"), p.get("name")): p for p in (state.get("pdbs") or [])}
    pdb_index: dict[str, dict] = {}
    for req in required_pdbs:
        got = submitted.get((req.get("namespace"), req.get("name")))
        if got is not None:
            pdb_index[str(req.get("name"))] = {
                **got,
                "required_min_available": req.get("min_available"),
                "selector": got.get("selector") or req.get("selector") or {},
            }

    total_evicted = 0
    total_blocked = 0
    pdb_respected = True
    for service in core_services:
        pdb = pdb_index.get(service)
        replicas = _resolve_replicas(service, pdb, deployments, defaults)
        if pdb is not None:
            try:
                floor = int(pdb.get("min_available", pdb.get("required_min_available") or 0))
            except (TypeError, ValueError):
                floor = 0
        else:
            floor = 1 if replicas > 0 else 0
        pods_on_node = 1 if replicas > 0 else 0
        max_evictable = max(0, replicas - floor)
        if pods_on_node == 0:
            availability[service] = False
            continue
        if max_evictable >= pods_on_node:
            remaining = replicas - pods_on_node
            total_evicted += pods_on_node
            respected = remaining >= floor
            available = remaining >= max(floor, 1) if floor else remaining > 0
        else:
            total_blocked += pods_on_node
            respected = False
            available = replicas >= max(floor, 1) if floor else replicas > 0
            remaining = replicas
        if pdb is not None and not respected:
            pdb_respected = False
        availability[service] = bool(available)

    core_available = all(availability.get(svc, False) for svc in core_services) and pdb_respected
    return (
        {
            "node": drain_node,
            "core_available": core_available,
            "evicted_count": total_evicted,
            "blocked_count": total_blocked,
        },
        availability,
        pdb_respected,
    )


def _simulate_interruption(
    graph: dict,
    placement_results: dict,
    regulated_policy: dict,
    defaults: dict,
) -> dict:
    """Mirror environment interruption_handler using curated events file."""
    reg_caps = {
        str(c).lower()
        for c in ((graph.get("regulated") or {}).get("capacity_types") or [])
    }
    placement_ok = bool(placement_results) and all(
        isinstance(v, dict) and v.get("ok") for v in placement_results.values()
    )
    placement_od = placement_ok and all(
        str(v.get("capacity_type") or "").lower() == "on-demand"
        for v in placement_results.values()
    )
    regulated_nodepool = str(
        ((regulated_policy.get("nodepool") or {}).get("name"))
        or (graph.get("regulated") or {}).get("name")
        or "regulated-on-demand"
    )
    regulated_workloads = [
        str(wl.get("name"))
        for wl in (regulated_policy.get("workloads") or [])
        if isinstance(wl, dict) and wl.get("name")
    ] or list(placement_results.keys())

    events_name = defaults.get("interruption_events_file") or "interruption_events.json"
    events_path = _data_dir() / str(events_name)
    events: list[dict] = []
    if events_path.is_file():
        try:
            payload = json.loads(events_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                events = [e for e in payload if isinstance(e, dict)]
        except (OSError, json.JSONDecodeError):
            events = []

    if not events:
        still = reg_caps == {"on-demand"} and placement_ok and placement_od
        return {"handled": False, "regulated_still_on_demand": still}

    still_on_demand = True
    handled = True
    relevant = 0
    for event in events:
        pool = str(event.get("nodepool") or "")
        affected = event.get("affected_workloads") or []
        targets = pool == regulated_nodepool or any(
            name in regulated_workloads for name in affected
        )
        if not targets:
            continue
        relevant += 1
        capacity = str(event.get("capacity_type") or "").lower()
        action = str(event.get("action") or "").lower()
        plan_od = reg_caps == {"on-demand"}
        allows_spot = "spot" in reg_caps
        if capacity == "spot" or action in {"rebalance", "terminate", "interrupt"}:
            if allows_spot or not plan_od or not placement_ok or not placement_od:
                still_on_demand = False
        elif capacity == "on-demand":
            if not (plan_od and placement_ok and placement_od):
                still_on_demand = False
        else:
            handled = False
            still_on_demand = False

    if relevant == 0:
        still_on_demand = reg_caps == {"on-demand"} and placement_ok and placement_od
        handled = True

    return {
        "handled": handled,
        "regulated_still_on_demand": still_on_demand and handled,
    }


def run_rollout(
    plan: dict,
    *,
    fail_addon: str | None = None,
    k8s_dir: Path | None = None,
) -> dict:
    """Plan-policy gate, apply manifests, roll addons, drain, interrupt."""
    snapshot = _load("cluster_snapshot.json")
    matrix = _load("compatibility_matrix.json")
    trust = _load("trust_observations.json")
    pdbs = _load("pdbs.json")
    regulated_policy = _load("regulated_policy.json")
    defaults = _load("defaults.json")

    var = _var_dir()
    out = _output_dir()
    var.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    (var / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

    graph = normalize_plan(plan)
    policy_errors = plan_policy_errors(
        graph, matrix, trust, defaults, regulated_policy, snapshot
    )

    order = upgrade_order(matrix)
    report: dict[str, Any] = {
        "status": "FAILED",
        "reason": None,
        "policy_errors": policy_errors,
        "upgrade_order": [],
        "steps": [],
        "availability": {name: False for name in defaults.get("core_services") or []},
        "pdb_respected": False,
        "drain_result": {
            "node": defaults.get("drain_node"),
            "core_available": False,
            "evicted_count": 0,
            "blocked_count": 0,
        },
        "irsa_bindings": {},
        "cross_service_denied": False,
        "regulated_placement": {},
        "interruption": {"handled": False, "regulated_still_on_demand": False},
        "report_digest": "",
    }

    if policy_errors:
        report["reason"] = "plan_policy"
        report["report_digest"] = _report_digest(report)
        _write_report(report)
        return report

    state = apply_k8s_manifests(k8s_dir)
    ok_pdb, pdb_errs = _pdb_coverage(state, pdbs.get("required") or [])
    if not ok_pdb:
        report["reason"] = "missing_pdbs"
        report["policy_errors"] = pdb_errs
        report["report_digest"] = _report_digest(report)
        _write_report(report)
        return report

    # Build role ARN map from plan roles
    role_arns: dict[str, str] = {}
    for _k, role in graph["roles"].items():
        tk = role["tags"].get("AddonTrust")
        if tk and role.get("name"):
            role_arns[tk] = (
                f"arn:aws:iam::{defaults['account_id']}:role/{role['name']}"
            )

    # Validate SA annotations match IRSA
    sa_index = {
        (s["namespace"], s["name"]): s for s in state.get("service_accounts") or []
    }
    subject_map = trust.get("required_subjects") or {}
    for trust_key, subject in subject_map.items():
        # system:serviceaccount:ns:name
        parts = subject.split(":")
        ns, name = parts[2], parts[3]
        sa = sa_index.get((ns, name))
        expected_arn = role_arns.get(trust_key, "")
        ok = bool(sa and sa.get("role_arn") == expected_arn and expected_arn)
        report["irsa_bindings"][trust_key] = {
            "subject": subject,
            "ok": ok,
            "role_arn": expected_arn,
        }
        if not ok:
            report["reason"] = "irsa_binding"
            report["report_digest"] = _report_digest(report)
            _write_report(report)
            return report

    # Cross-service denial: each role subject distinct; no shared ARN across keys
    arns = [v["role_arn"] for v in report["irsa_bindings"].values()]
    report["cross_service_denied"] = len(arns) == len(set(arns)) == len(subject_map)
    if not report["cross_service_denied"]:
        report["reason"] = "cross_service_trust"
        report["report_digest"] = _report_digest(report)
        _write_report(report)
        return report

    # Simulate addon rollout in order
    checkpoint_path = var / "checkpoint.json"
    prior: dict[str, Any] = {}
    if checkpoint_path.is_file():
        try:
            prior = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prior = {}
    ready: set[str] = set(prior.get("ready") or [])
    report["upgrade_order"] = list(prior.get("upgrade_order") or [])
    report["steps"] = list(prior.get("steps") or [])
    installed = dict(snapshot.get("addons") or {})
    for cname, cmeta in (snapshot.get("controllers") or {}).items():
        installed[cname] = cmeta
    for done in report["upgrade_order"]:
        planned_done = graph["addons"].get(done) or {}
        installed[done] = {
            "installed": planned_done.get("addon_version"),
            "status": "ACTIVE",
        }

    def _save_ckpt() -> None:
        checkpoint_path.write_text(
            json.dumps(
                {
                    "ready": sorted(ready),
                    "upgrade_order": list(report["upgrade_order"]),
                    "steps": list(report["steps"]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    for name in order:
        if name in ready:
            continue
        meta = (matrix.get("addons") or {})[name]
        reqs = meta.get("requires") or []
        if not all(r in ready for r in reqs):
            report["reason"] = f"prerequisite_missing:{name}"
            _save_ckpt()
            report["report_digest"] = _report_digest(report)
            _write_report(report)
            return report

        if fail_addon and name == fail_addon:
            report["steps"].append(
                {
                    "addon": name,
                    "from_version": (installed.get(name) or {}).get("installed"),
                    "to_version": meta.get("target"),
                    "ok": False,
                }
            )
            report["reason"] = f"readiness_failed:{name}"
            _save_ckpt()
            report["report_digest"] = _report_digest(report)
            _write_report(report)
            return report

        planned = graph["addons"][name]
        report["steps"].append(
            {
                "addon": name,
                "from_version": (installed.get(name) or {}).get("installed"),
                "to_version": planned.get("addon_version"),
                "ok": True,
            }
        )
        report["upgrade_order"].append(name)
        ready.add(name)
        installed[name] = {"installed": planned.get("addon_version"), "status": "ACTIVE"}
        _save_ckpt()

    # Availability + drain simulation from PDB thresholds and replica capacity
    drain_result, availability, pdb_respected = _simulate_drain(
        defaults,
        state,
        pdbs.get("required") or [],
    )
    report["drain_result"] = drain_result
    report["availability"] = availability
    report["pdb_respected"] = pdb_respected
    if not pdb_respected or not drain_result.get("core_available"):
        report["reason"] = "drain_availability"
        report["report_digest"] = _report_digest(report)
        _write_report(report)
        return report

    # Regulated workloads
    for wl in regulated_policy.get("workloads") or []:
        match = next(
            (
                w
                for w in state.get("workloads") or []
                if w.get("name") == wl["name"]
            ),
            None,
        )
        # Also accept regulated nodepool doc
        nodepool_ok = False
        for np in state.get("nodepools") or []:
            meta = np.get("metadata") or {}
            if meta.get("name") == wl["required_nodepool"]:
                reqs = ((np.get("spec") or {}).get("template") or {}).get("spec") or {}
                req_list = reqs.get("requirements") or []
                caps = []
                for req in req_list:
                    if req.get("key") == "karpenter.sh/capacity-type":
                        caps = list(req.get("values") or [])
                nodepool_ok = caps == ["on-demand"]
        placement_ok = bool(
            match
            and match.get("nodepool") == wl["required_nodepool"]
            and match.get("capacity_type") == wl["capacity_type"]
        ) or nodepool_ok
        # Prefer explicit workload selectors when present
        if match:
            placement_ok = (
                match.get("nodepool") == wl["required_nodepool"]
                and match.get("capacity_type") == wl["capacity_type"]
            )
        report["regulated_placement"][wl["name"]] = {
            "nodepool": wl["required_nodepool"],
            "capacity_type": wl["capacity_type"],
            "ok": placement_ok,
        }
        if not placement_ok:
            report["reason"] = "regulated_placement"
            report["report_digest"] = _report_digest(report)
            _write_report(report)
            return report

    # Interruption: evaluate curated events against plan capacity + placement
    interruption = _simulate_interruption(
        graph,
        report["regulated_placement"],
        regulated_policy,
        defaults,
    )
    report["interruption"] = {
        "handled": bool(interruption.get("handled")),
        "regulated_still_on_demand": bool(
            interruption.get("regulated_still_on_demand")
        ),
    }
    if not report["interruption"]["regulated_still_on_demand"]:
        report["reason"] = "interruption_placement"
        report["report_digest"] = _report_digest(report)
        _write_report(report)
        return report

    report["status"] = "READY"
    report["reason"] = None
    if checkpoint_path.is_file():
        checkpoint_path.unlink()
    report["report_digest"] = _report_digest(report)
    _write_report(report)
    return report


def _report_digest(report: dict) -> str:
    drain = report.get("drain_result") or {}
    interruption = report.get("interruption") or {}
    stable = {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "policy_errors": sorted(report.get("policy_errors") or []),
        "upgrade_order": report.get("upgrade_order") or [],
        "steps": report.get("steps") or [],
        "availability": report.get("availability") or {},
        "pdb_respected": report.get("pdb_respected", False),
        "drain_result": {
            "node": drain.get("node"),
            "core_available": bool(drain.get("core_available", False)),
            "evicted_count": int(drain.get("evicted_count") or 0),
            "blocked_count": int(drain.get("blocked_count") or 0),
        },
        "irsa_bindings": {
            k: {"subject": v.get("subject"), "ok": v.get("ok")}
            for k, v in sorted((report.get("irsa_bindings") or {}).items())
        },
        "cross_service_denied": report.get("cross_service_denied", False),
        "regulated_placement": report.get("regulated_placement") or {},
        "interruption": {
            "handled": bool(interruption.get("handled", False)),
            "regulated_still_on_demand": bool(
                interruption.get("regulated_still_on_demand", False)
            ),
        },
    }
    return _stable_digest(stable)


def _write_report(report: dict) -> None:
    out = _output_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / "upgrade-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
