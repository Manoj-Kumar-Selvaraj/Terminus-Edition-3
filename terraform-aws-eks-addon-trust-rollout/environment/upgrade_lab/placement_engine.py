"""Regulated workload placement and Karpenter NodePool CRD evaluator."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def evaluate_regulated_placement(
    k8s_state: Dict[str, Any],
    regulated_policy: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Evaluate whether regulated workloads are placed exclusively on approved on-demand node pools."""
    placement_results: Dict[str, Any] = {}
    all_ok = True
    errors: List[str] = []

    workload_policies = regulated_policy.get("workloads") or []
    submitted_workloads = k8s_state.get("workloads") or []
    submitted_nodepools = k8s_state.get("nodepools") or []

    for wl in workload_policies:
        match = next(
            (w for w in submitted_workloads if w.get("name") == wl["name"]),
            None,
        )

        nodepool_ok = False
        for np in submitted_nodepools:
            meta = np.get("metadata") or {}
            if meta.get("name") == wl["required_nodepool"]:
                template_spec = ((np.get("spec") or {}).get("template") or {}).get("spec") or {}
                reqs = template_spec.get("requirements") or []
                caps = []
                for req in reqs:
                    if req.get("key") == "karpenter.sh/capacity-type":
                        caps = list(req.get("values") or [])
                nodepool_ok = (caps == ["on-demand"])

        placement_ok = bool(
            match
            and match.get("nodepool") == wl["required_nodepool"]
            and match.get("capacity_type") == wl["capacity_type"]
        ) or nodepool_ok

        if match:
            placement_ok = (
                match.get("nodepool") == wl["required_nodepool"]
                and match.get("capacity_type") == wl["capacity_type"]
            )

        placement_results[wl["name"]] = {
            "nodepool": wl["required_nodepool"],
            "capacity_type": wl["capacity_type"],
            "ok": placement_ok,
        }

        if not placement_ok:
            all_ok = False
            errors.append(f"Regulated placement policy failed for workload {wl['name']}")

    return placement_results, all_ok, errors
