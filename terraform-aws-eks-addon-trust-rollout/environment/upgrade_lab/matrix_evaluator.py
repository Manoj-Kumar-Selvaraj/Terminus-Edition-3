"""Add-on compatibility matrix and prerequisite dependency graph evaluator."""
from __future__ import annotations

from typing import Any, Dict, List


def get_upgrade_order(matrix: Dict[str, Any]) -> List[str]:
    """Return add-on names sorted in compatibility matrix rollout order."""
    addons = matrix.get("addons") or {}
    return [
        name for name, _meta in sorted(addons.items(), key=lambda kv: kv[1].get("order", 0))
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
