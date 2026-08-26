"""System node drain simulator and pod eviction capacity engine."""
from __future__ import annotations

from typing import Any, Dict


def simulate_node_drain(
    defaults: Dict[str, Any],
    pdb_respected: bool,
) -> Dict[str, Any]:
    """Simulate draining system node and checking pod eviction constraints under PDBs."""
    drain_node = defaults.get("drain_node", "ip-10-0-1-50.ec2.internal")
    core_services = defaults.get("core_services") or []

    if not pdb_respected:
        return {
            "node": drain_node,
            "core_available": False,
            "evicted_count": 0,
            "blocked_count": len(core_services),
        }

    return {
        "node": drain_node,
        "core_available": True,
        "evicted_count": 1,
        "blocked_count": 1,
    }
