"""PodDisruptionBudget coverage and minAvailable threshold analyzer."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def evaluate_pdb_coverage(
    k8s_pdbs: List[Dict[str, Any]],
    required_pdbs: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Verify submitted PDB manifests cover all required services with exact minAvailable thresholds."""
    missing: List[str] = []
    have = {(p["namespace"], p["name"]): p for p in k8s_pdbs}

    for req in required_pdbs:
        key = (req["namespace"], req["name"])
        got = have.get(key)
        if not got:
            missing.append(f"missing pdb {req['namespace']}/{req['name']}")
            continue
        if got.get("min_available") != req.get("min_available"):
            missing.append(f"pdb {req['name']} minAvailable mismatch")

    return len(missing) == 0, missing
