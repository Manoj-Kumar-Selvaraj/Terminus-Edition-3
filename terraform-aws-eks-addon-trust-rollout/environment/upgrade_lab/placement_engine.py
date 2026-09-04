"""Regulated workload placement and Karpenter NodePool CRD evaluator."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def _capacity_values(requirements: Sequence[Dict[str, Any]]) -> List[str]:
    caps: List[str] = []
    for req in requirements:
        if not isinstance(req, dict):
            continue
        if req.get("key") != "karpenter.sh/capacity-type":
            continue
        caps = [str(v) for v in (req.get("values") or [])]
    return caps


def _nodepool_capacity_types(nodepool_doc: Dict[str, Any]) -> List[str]:
    template_spec = ((nodepool_doc.get("spec") or {}).get("template") or {}).get("spec") or {}
    return _capacity_values(template_spec.get("requirements") or [])


def _find_nodepool(nodepools: Sequence[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for np in nodepools:
        meta = np.get("metadata") or {}
        if meta.get("name") == name and np.get("kind") in {None, "NodePool"}:
            # Prefer explicit NodePool kind when present.
            if np.get("kind") == "NodePool" or np.get("kind") is None:
                return np
    for np in nodepools:
        meta = np.get("metadata") or {}
        if meta.get("name") == name:
            return np
    return None


def _ec2_nodeclass_private_only(nodepools: Sequence[Dict[str, Any]], class_name: str) -> Optional[bool]:
    for doc in nodepools:
        if doc.get("kind") != "EC2NodeClass":
            continue
        meta = doc.get("metadata") or {}
        if meta.get("name") != class_name:
            continue
        spec = doc.get("spec") or {}
        terms = spec.get("subnetSelectorTerms") or []
        if not terms:
            return None
        private_markers = 0
        public_markers = 0
        for term in terms:
            tags = (term or {}).get("tags") or {}
            joined = " ".join(f"{k}={v}" for k, v in tags.items()).lower()
            if "private" in joined or "subnettype=private" in joined.replace(" ", ""):
                private_markers += 1
            if "public" in joined or "subnettype=public" in joined.replace(" ", ""):
                public_markers += 1
        if private_markers and not public_markers:
            return True
        if public_markers:
            return False
    return None


def evaluate_workload_placement(
    workload_policy: Dict[str, Any],
    submitted_workloads: Sequence[Dict[str, Any]],
    submitted_nodepools: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Evaluate one regulated workload against selectors and NodePool CRD."""
    errors: List[str] = []
    name = workload_policy.get("name")
    required_pool = workload_policy.get("required_nodepool")
    required_capacity = workload_policy.get("capacity_type")

    match = next((w for w in submitted_workloads if w.get("name") == name), None)
    np_doc = _find_nodepool(submitted_nodepools, str(required_pool))
    nodepool_caps = _nodepool_capacity_types(np_doc) if np_doc else []
    nodepool_ok = nodepool_caps == [required_capacity] if required_capacity else False

    # Prefer explicit workload selectors when the Deployment/StatefulSet is present.
    if match:
        placement_ok = (
            match.get("nodepool") == required_pool
            and match.get("capacity_type") == required_capacity
        )
        if not placement_ok:
            errors.append(
                f"workload {name} selector mismatch "
                f"(nodepool={match.get('nodepool')}, capacity={match.get('capacity_type')})"
            )
    else:
        # Fallback: NodePool CRD alone can satisfy fencing when workload manifest is absent.
        placement_ok = nodepool_ok
        if not placement_ok:
            errors.append(f"Regulated placement policy failed for workload {name}")

    # Even with matching selectors, NodePool must not advertise spot.
    if np_doc is not None:
        if "spot" in {c.lower() for c in nodepool_caps}:
            placement_ok = False
            errors.append(f"NodePool {required_pool} allows spot capacity")
        if required_capacity and nodepool_caps and nodepool_caps != [required_capacity]:
            # Workload selectors win for placement_ok already; still record CRD drift.
            if match and placement_ok and nodepool_caps != [required_capacity]:
                placement_ok = False
                errors.append(f"NodePool {required_pool} capacity drift")

        # Optional private subnet signal from referenced EC2NodeClass.
        class_ref = (
            ((np_doc.get("spec") or {}).get("template") or {}).get("spec") or {}
        ).get("nodeClassRef") or {}
        class_name = class_ref.get("name")
        if class_name:
            private = _ec2_nodeclass_private_only(submitted_nodepools, str(class_name))
            if private is False:
                placement_ok = False
                errors.append(f"EC2NodeClass {class_name} is not private-subnet only")

    result = {
        "nodepool": required_pool,
        "capacity_type": required_capacity,
        "ok": bool(placement_ok),
        "workload_found": match is not None,
        "nodepool_found": np_doc is not None,
        "nodepool_capacity_types": list(nodepool_caps),
    }
    return result, bool(placement_ok), errors


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

    if not workload_policies:
        return {}, False, ["regulated policy defines no workloads"]

    for wl in workload_policies:
        result, ok, errs = evaluate_workload_placement(
            wl, submitted_workloads, submitted_nodepools
        )
        # Report schema requires nodepool/capacity_type/ok keys.
        placement_results[str(wl.get("name"))] = {
            "nodepool": result.get("nodepool"),
            "capacity_type": result.get("capacity_type"),
            "ok": result.get("ok"),
        }
        if not ok:
            all_ok = False
            if errs:
                errors.extend(errs)
            else:
                errors.append(
                    f"Regulated placement policy failed for workload {wl.get('name')}"
                )

    return placement_results, all_ok, list(dict.fromkeys(errors))
