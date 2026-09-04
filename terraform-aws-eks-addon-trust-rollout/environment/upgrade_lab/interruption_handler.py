"""Spot / on-demand node interruption simulator and capacity fence analyzer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def load_interruption_events(path: Path) -> List[Dict[str, Any]]:
    """Load curated interruption events; empty list when missing or invalid."""
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return [e for e in payload["events"] if isinstance(e, dict)]
    return []


def _capacity_set(values: Any) -> set[str]:
    if not values:
        return set()
    if isinstance(values, str):
        return {v.strip().lower() for v in values.split(",") if v.strip()}
    return {str(v).strip().lower() for v in values if str(v).strip()}


def _placement_on_demand(placement_results: Dict[str, Any]) -> bool:
    if not placement_results:
        return False
    for meta in placement_results.values():
        if not isinstance(meta, dict):
            return False
        if not meta.get("ok", False):
            return False
        if str(meta.get("capacity_type") or "").lower() != "on-demand":
            return False
    return True


def _event_targets_regulated(
    event: Dict[str, Any],
    regulated_workloads: Sequence[str],
    regulated_nodepool: str,
) -> bool:
    pool = str(event.get("nodepool") or "")
    affected = event.get("affected_workloads") or []
    if pool == regulated_nodepool:
        return True
    if any(name in regulated_workloads for name in affected):
        return True
    return False


def evaluate_interruption_event(
    event: Dict[str, Any],
    *,
    graph_capacity_types: set[str],
    placement_ok: bool,
    placement_on_demand: bool,
    regulated_nodepool: str,
    regulated_workloads: Sequence[str],
) -> Dict[str, Any]:
    """
    Evaluate a single interruption/rebalance event against regulated fencing.

    Spot interruptions on the regulated pool require on-demand-only Terraform
    capacity and healthy on-demand placement. Non-regulated events are ignored.
    """
    event_id = str(event.get("event_id") or event.get("id") or "unknown")
    capacity = str(event.get("capacity_type") or "").lower()
    action = str(event.get("action") or "").lower()
    targets = _event_targets_regulated(event, regulated_workloads, regulated_nodepool)

    if not targets:
        return {
            "event_id": event_id,
            "relevant": False,
            "handled": True,
            "regulated_still_on_demand": True,
            "reason": "non_regulated_scope",
        }

    # Regulated pool must not rely on spot capacity in the plan.
    plan_is_on_demand = graph_capacity_types == {"on-demand"}
    allows_spot = "spot" in graph_capacity_types

    if capacity == "spot" or action in {"rebalance", "terminate", "interrupt"}:
        if allows_spot:
            return {
                "event_id": event_id,
                "relevant": True,
                "handled": True,
                "regulated_still_on_demand": False,
                "reason": "plan_allows_spot",
            }
        if not plan_is_on_demand:
            return {
                "event_id": event_id,
                "relevant": True,
                "handled": True,
                "regulated_still_on_demand": False,
                "reason": "plan_capacity_not_on_demand",
            }
        if not placement_ok or not placement_on_demand:
            return {
                "event_id": event_id,
                "relevant": True,
                "handled": True,
                "regulated_still_on_demand": False,
                "reason": "placement_not_on_demand",
            }
        return {
            "event_id": event_id,
            "relevant": True,
            "handled": True,
            "regulated_still_on_demand": True,
            "reason": "rebalanced_to_on_demand",
        }

    if capacity == "on-demand":
        # On-demand maintenance is safe only when placement already fences on-demand.
        still = plan_is_on_demand and placement_ok and placement_on_demand
        return {
            "event_id": event_id,
            "relevant": True,
            "handled": True,
            "regulated_still_on_demand": still,
            "reason": "on_demand_maintenance" if still else "on_demand_fence_failed",
        }

    return {
        "event_id": event_id,
        "relevant": True,
        "handled": False,
        "regulated_still_on_demand": False,
        "reason": f"unsupported_capacity:{capacity or 'empty'}",
    }


def simulate_node_interruption(
    graph: Dict[str, Any],
    placement_results: Dict[str, Any],
    *,
    events: Optional[List[Dict[str, Any]]] = None,
    events_path: Optional[Path] = None,
    regulated_policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Simulate capacity rebalancing from curated interruption events and verify
    regulated workloads remain on on-demand capacity afterward.
    """
    reg = graph.get("regulated") or {}
    reg_caps = _capacity_set(reg.get("capacity_types"))
    placement_ok = bool(placement_results) and all(
        isinstance(v, dict) and v.get("ok", False) for v in placement_results.values()
    )
    placement_od = _placement_on_demand(placement_results)

    policy = regulated_policy or {}
    regulated_nodepool = str((policy.get("nodepool") or {}).get("name") or reg.get("name") or "regulated-on-demand")
    regulated_workloads = [
        str(wl.get("name"))
        for wl in (policy.get("workloads") or [])
        if isinstance(wl, dict) and wl.get("name")
    ]
    if not regulated_workloads:
        regulated_workloads = list(placement_results.keys())

    loaded = list(events) if events is not None else []
    if not loaded and events_path is not None:
        loaded = load_interruption_events(events_path)

    if not loaded:
        # Fail closed when curated events are expected but absent.
        still = reg_caps == {"on-demand"} and placement_ok and placement_od
        return {
            "handled": False,
            "regulated_still_on_demand": still,
            "events_evaluated": 0,
            "relevant_events": 0,
            "details": [],
            "reason": "missing_interruption_events",
        }

    details: List[Dict[str, Any]] = []
    still_on_demand = True
    handled = True
    relevant_count = 0

    for event in loaded:
        outcome = evaluate_interruption_event(
            event,
            graph_capacity_types=reg_caps,
            placement_ok=placement_ok,
            placement_on_demand=placement_od,
            regulated_nodepool=regulated_nodepool,
            regulated_workloads=regulated_workloads,
        )
        details.append(outcome)
        if outcome.get("relevant"):
            relevant_count += 1
            if not outcome.get("handled", False):
                handled = False
            if not outcome.get("regulated_still_on_demand", False):
                still_on_demand = False

    if relevant_count == 0:
        # No regulated-scoped events: fall back to plan+placement fence.
        still_on_demand = reg_caps == {"on-demand"} and placement_ok and placement_od
        handled = True

    return {
        "handled": handled,
        "regulated_still_on_demand": still_on_demand and handled,
        "events_evaluated": len(loaded),
        "relevant_events": relevant_count,
        "details": details,
    }
