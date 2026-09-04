"""PodDisruptionBudget coverage and minAvailable threshold analyzer."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _coerce_min_available(raw: Any) -> Any:
    """Preserve ints; normalize numeric strings; leave percentages as strings."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if text.endswith("%"):
            return text
        try:
            return int(text)
        except ValueError:
            return text
    return raw


def index_pdbs(pdbs: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(p.get("namespace") or "default"), str(p.get("name") or "")): p
        for p in pdbs
        if isinstance(p, dict)
    }


def selector_equal(got: Any, expected: Any) -> bool:
    if not isinstance(got, dict) or not isinstance(expected, dict):
        return False
    if set(got.keys()) != set(expected.keys()):
        return False
    for key, value in expected.items():
        if got.get(key) != value:
            return False
    return True


def evaluate_single_pdb(
    required: Dict[str, Any],
    submitted: Optional[Dict[str, Any]],
) -> List[str]:
    """Return validation errors for one required PDB entry."""
    name = required.get("name")
    namespace = required.get("namespace")
    errors: List[str] = []
    if submitted is None:
        errors.append(f"missing pdb {namespace}/{name}")
        return errors

    got_min = _coerce_min_available(submitted.get("min_available"))
    want_min = _coerce_min_available(required.get("min_available"))
    if got_min != want_min:
        errors.append(f"pdb {name} minAvailable mismatch")

    return errors


def evaluate_pdb_coverage(
    k8s_pdbs: List[Dict[str, Any]],
    required_pdbs: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """Verify submitted PDB manifests cover all required services with exact minAvailable thresholds."""
    missing: List[str] = []
    have = index_pdbs(k8s_pdbs)

    for req in required_pdbs:
        key = (str(req.get("namespace") or "default"), str(req.get("name") or ""))
        got = have.get(key)
        missing.extend(evaluate_single_pdb(req, got))

    # Detect duplicate PDB names that can confuse drain matching.
    seen_names: Dict[str, int] = {}
    for pdb in k8s_pdbs:
        n = str(pdb.get("name") or "")
        seen_names[n] = seen_names.get(n, 0) + 1
    for name, count in seen_names.items():
        if name and count > 1:
            missing.append(f"duplicate pdb name {name}")

    return len(missing) == 0, list(dict.fromkeys(missing))


def pdb_threshold_map(
    k8s_pdbs: List[Dict[str, Any]],
    required_pdbs: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Map PDB name -> effective minAvailable for drain simulation."""
    have = index_pdbs(k8s_pdbs)
    thresholds: Dict[str, int] = {}
    for req in required_pdbs:
        key = (str(req.get("namespace") or "default"), str(req.get("name") or ""))
        got = have.get(key) or {}
        raw = got.get("min_available", req.get("min_available"))
        coerced = _coerce_min_available(raw)
        if isinstance(coerced, int):
            thresholds[str(req.get("name"))] = coerced
    return thresholds
