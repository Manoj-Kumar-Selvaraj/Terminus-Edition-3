"""System node drain simulator and pod eviction capacity engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_min_available(raw: Any, replicas: int) -> Optional[int]:
    """Convert minAvailable int or percentage string into an absolute floor."""
    if raw is None:
        return None
    if isinstance(raw, str) and raw.endswith("%"):
        try:
            pct = float(raw[:-1])
        except ValueError:
            return None
        if pct < 0 or pct > 100:
            return None
        return max(0, int((pct / 100.0) * replicas))
    return _as_int(raw, default=-1) if _as_int(raw, default=-1) >= 0 else None


def _selector_matches(labels: Dict[str, Any], selector: Dict[str, Any]) -> bool:
    if not selector:
        return False
    for key, expected in selector.items():
        if labels.get(key) != expected:
            return False
    return True


def _deployment_replicas_for_pdb(
    pdb: Dict[str, Any],
    deployments: List[Dict[str, Any]],
) -> Optional[int]:
    """Find a deployment whose pod labels match the PDB selector."""
    selector = pdb.get("selector") or {}
    namespace = pdb.get("namespace") or "default"
    for dep in deployments:
        if (dep.get("namespace") or "default") != namespace:
            continue
        labels = dep.get("labels") or {}
        if _selector_matches(labels, selector):
            return max(0, _as_int(dep.get("replicas"), 0))
    # Fallback: deployment named like the PDB in the same namespace
    for dep in deployments:
        if (dep.get("namespace") or "default") != namespace:
            continue
        if dep.get("name") == pdb.get("name"):
            return max(0, _as_int(dep.get("replicas"), 0))
    return None


def _resolve_service_replicas(
    service_name: str,
    pdb: Optional[Dict[str, Any]],
    deployments: List[Dict[str, Any]],
    defaults: Dict[str, Any],
) -> int:
    """Resolve replica count from matching deployment, else defaults inventory."""
    if pdb is not None:
        matched = _deployment_replicas_for_pdb(pdb, deployments)
        if matched is not None:
            return matched
    fallback = (defaults.get("core_service_replicas") or {}).get(service_name)
    if fallback is not None:
        return max(0, _as_int(fallback, 0))
    return 0


def evaluate_pdb_drain_capacity(
    *,
    service_name: str,
    replicas: int,
    min_available: Optional[int],
    pods_on_drain_node: int = 1,
) -> Dict[str, Any]:
    """
    Evaluate whether draining one system node can evict pods without
    dropping below the PDB minAvailable floor.
    """
    if replicas <= 0:
        return {
            "service": service_name,
            "replicas": replicas,
            "min_available": min_available,
            "evictable": 0,
            "evicted": 0,
            "blocked": pods_on_drain_node,
            "remaining": 0,
            "respected": False,
            "available": False,
            "reason": "no_replicas",
        }

    floor = 0 if min_available is None else max(0, min_available)
    max_evictable = max(0, replicas - floor)
    requested = max(0, pods_on_drain_node)

    if requested == 0:
        return {
            "service": service_name,
            "replicas": replicas,
            "min_available": floor,
            "evictable": max_evictable,
            "evicted": 0,
            "blocked": 0,
            "remaining": replicas,
            "respected": True,
            "available": replicas >= max(floor, 1) if floor else replicas > 0,
            "reason": "nothing_to_drain",
        }

    if max_evictable >= requested:
        remaining = replicas - requested
        return {
            "service": service_name,
            "replicas": replicas,
            "min_available": floor,
            "evictable": max_evictable,
            "evicted": requested,
            "blocked": 0,
            "remaining": remaining,
            "respected": remaining >= floor,
            "available": remaining >= max(floor, 1) if floor else remaining > 0,
            "reason": "evicted",
        }

    # Cannot evict without violating PDB: pods remain, drain blocked for this service.
    return {
        "service": service_name,
        "replicas": replicas,
        "min_available": floor,
        "evictable": max_evictable,
        "evicted": 0,
        "blocked": requested,
        "remaining": replicas,
        "respected": False,
        "available": replicas >= max(floor, 1) if floor else replicas > 0,
        "reason": "pdb_blocks_eviction",
    }


def index_required_pdbs(
    required_pdbs: List[Dict[str, Any]],
    submitted_pdbs: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Map required PDB name -> submitted PDB record (same namespace/name)."""
    have = {
        (p.get("namespace"), p.get("name")): p for p in (submitted_pdbs or [])
    }
    indexed: Dict[str, Dict[str, Any]] = {}
    for req in required_pdbs or []:
        key = (req.get("namespace"), req.get("name"))
        got = have.get(key)
        if got is not None:
            indexed[str(req.get("name"))] = {
                **got,
                "required_min_available": req.get("min_available"),
                "required_selector": req.get("selector") or {},
            }
    return indexed


def simulate_node_drain(
    defaults: Dict[str, Any],
    *,
    k8s_state: Optional[Dict[str, Any]] = None,
    required_pdbs: Optional[List[Dict[str, Any]]] = None,
    pdb_coverage_ok: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, bool], bool]:
    """
    Simulate draining the configured system node.

    Eviction counts are derived from PDB minAvailable thresholds and deployment
    (or defaults) replica capacity. Returns drain_result, availability map, and
    whether every PDB budget was respected.
    """
    drain_node = defaults.get("drain_node", "ip-10-0-1-10.ec2.internal")
    core_services = list(defaults.get("core_services") or [])
    state = k8s_state or {}
    deployments = list(state.get("deployments") or [])
    submitted_pdbs = list(state.get("pdbs") or [])
    required = list(required_pdbs or [])

    availability: Dict[str, bool] = {name: False for name in core_services}
    if not pdb_coverage_ok:
        return (
            {
                "node": drain_node,
                "core_available": False,
                "evicted_count": 0,
                "blocked_count": len(core_services),
            },
            availability,
            False,
        )

    pdb_index = index_required_pdbs(required, submitted_pdbs)
    per_service: List[Dict[str, Any]] = []
    total_evicted = 0
    total_blocked = 0
    pdb_respected = True

    for service in core_services:
        pdb = pdb_index.get(service)
        replicas = _resolve_service_replicas(service, pdb, deployments, defaults)
        if pdb is not None:
            min_available = _normalize_min_available(
                pdb.get("min_available", pdb.get("required_min_available")),
                replicas,
            )
            # Prefer required threshold when submitted value is present but coverage already matched
            if pdb.get("required_min_available") is not None:
                req_floor = _normalize_min_available(pdb.get("required_min_available"), replicas)
                if req_floor is not None:
                    min_available = req_floor
        else:
            # Services without a required PDB (e.g. vpc-cni) stay available if replicas remain.
            min_available = 1 if replicas > 0 else 0

        # One pod of each core service is assumed present on the drain target node.
        pods_on_node = 1 if replicas > 0 else 0
        outcome = evaluate_pdb_drain_capacity(
            service_name=service,
            replicas=replicas,
            min_available=min_available,
            pods_on_drain_node=pods_on_node,
        )
        per_service.append(outcome)
        total_evicted += int(outcome["evicted"])
        total_blocked += int(outcome["blocked"])
        if pdb is not None and not outcome["respected"]:
            pdb_respected = False
        availability[service] = bool(outcome["available"])

    core_available = all(availability.get(svc, False) for svc in core_services) and pdb_respected

    # When every PDB allows a single eviction and capacity remains, counts are non-zero.
    drain_result = {
        "node": drain_node,
        "core_available": core_available,
        "evicted_count": total_evicted,
        "blocked_count": total_blocked,
    }
    return drain_result, availability, pdb_respected
