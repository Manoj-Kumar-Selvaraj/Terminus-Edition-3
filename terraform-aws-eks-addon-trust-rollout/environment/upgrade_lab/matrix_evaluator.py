"""Add-on compatibility matrix and prerequisite dependency graph evaluator."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


def get_upgrade_order(matrix: Dict[str, Any]) -> List[str]:
    """Return add-on names sorted in compatibility matrix rollout order."""
    addons = matrix.get("addons") or {}
    return [
        name
        for name, _meta in sorted(
            addons.items(), key=lambda kv: (kv[1].get("order", 0), kv[0])
        )
    ]


def validate_prerequisites(
    addon_name: str,
    matrix: Dict[str, Any],
    ready_addons: set[str],
) -> tuple[bool, List[str]]:
    """Check whether all prerequisite add-ons are ready before advancing addon_name."""
    addons_meta = matrix.get("addons") or {}
    meta = addons_meta.get(addon_name) or {}
    required = meta.get("requires") or []
    missing = [req for req in required if req not in ready_addons]
    return len(missing) == 0, missing


def build_dependency_graph(matrix: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return adjacency map of addon -> direct prerequisites."""
    graph: Dict[str, List[str]] = {}
    for name, meta in (matrix.get("addons") or {}).items():
        graph[str(name)] = [str(r) for r in (meta.get("requires") or [])]
    return graph


def detect_dependency_cycles(matrix: Dict[str, Any]) -> List[str]:
    """Return list of addons involved in prerequisite cycles, if any."""
    graph = build_dependency_graph(matrix)
    visiting: Set[str] = set()
    visited: Set[str] = set()
    cyclic: List[str] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cyclic.append(node)
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            dfs(dep)
        visiting.remove(node)
        visited.add(node)

    for name in graph:
        dfs(name)
    return list(dict.fromkeys(cyclic))


def validate_matrix_integrity(matrix: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate order uniqueness, known prerequisites, and acyclic dependencies."""
    errors: List[str] = []
    addons = matrix.get("addons") or {}
    if not addons:
        return False, ["compatibility matrix has no addons"]

    orders = [meta.get("order") for meta in addons.values()]
    if len(orders) != len(set(orders)):
        errors.append("compatibility matrix order values must be unique")

    known = set(addons.keys())
    for name, meta in addons.items():
        for req in meta.get("requires") or []:
            if req not in known:
                errors.append(f"{name}: unknown prerequisite {req}")
        if meta.get("target") in (None, ""):
            errors.append(f"{name}: missing target version")

    cycles = detect_dependency_cycles(matrix)
    if cycles:
        errors.append(f"compatibility matrix has cycles involving {','.join(cycles)}")

    return len(errors) == 0, errors


def readiness_gate(
    addon_name: str,
    *,
    matrix: Dict[str, Any],
    ready: Set[str],
    fail_addon: str | None = None,
) -> Tuple[bool, str | None]:
    """
    Combined prerequisite + simulated readiness gate used by the coordinator.

    Returns (ok, reason_suffix). reason_suffix is None when the addon may proceed.
    """
    ok, missing = validate_prerequisites(addon_name, matrix, ready)
    if not ok:
        return False, f"prerequisite_missing:{addon_name}"
    if fail_addon and addon_name == fail_addon:
        return False, f"readiness_failed:{addon_name}"
    return True, None
