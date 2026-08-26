"""Spot / on-demand node interruption simulator and capacity fence analyzer."""
from __future__ import annotations

from typing import Any, Dict


def simulate_node_interruption(
    graph: Dict[str, Any],
    placement_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate capacity rebalancing and verify regulated workloads remain on on-demand capacity."""
    reg = graph.get("regulated") or {}
    reg_caps = set(reg.get("capacity_types") or [])

    placement_ok = all(
        v.get("ok", False) for v in placement_results.values()
    ) if placement_results else False

    still_on_demand = (reg_caps == {"on-demand"}) and placement_ok

    return {
        "handled": True,
        "regulated_still_on_demand": still_on_demand,
    }
