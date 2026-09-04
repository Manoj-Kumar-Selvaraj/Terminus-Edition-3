"""Add-on readiness polling helpers used by the rollout coordinator."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


TERMINAL_ACTIVE = {"ACTIVE", "READY", "HEALTHY"}
TERMINAL_FAILED = {"DEGRADED", "FAILED", "CREATE_FAILED", "UPDATE_FAILED"}


def normalize_status(raw: Any) -> str:
    return str(raw or "").strip().upper()


def is_addon_ready(status: Any) -> bool:
    return normalize_status(status) in TERMINAL_ACTIVE


def is_addon_failed(status: Any) -> bool:
    return normalize_status(status) in TERMINAL_FAILED


def poll_addon_readiness(
    name: str,
    *,
    installed: Dict[str, Any],
    planned_version: Optional[str],
    target_version: Optional[str],
    require_version_match: bool = True,
) -> Tuple[bool, str]:
    """
    Evaluate whether an add-on may be marked complete.

    Returns (ready, detail). detail is a short reason string for failed gates.
    """
    meta = installed.get(name) or {}
    status = normalize_status(meta.get("status"))
    if is_addon_failed(status):
        return False, f"addon {name} status {status or 'UNKNOWN'}"
    # After a successful step the coordinator stamps ACTIVE; before that, absence is OK
    # when the planned version is about to be applied.
    if status and not is_addon_ready(status) and status not in {"", "UNKNOWN"}:
        # Non-terminal transitional statuses block completion.
        if status not in {"CREATING", "UPDATING", "DELETING"}:
            return False, f"addon {name} not ready ({status})"

    if require_version_match and planned_version and target_version:
        if planned_version != target_version:
            return False, f"addon {name} planned version drift"

    return True, "ready"


def verify_step_completion(
    name: str,
    *,
    matrix: Dict[str, Any],
    planned: Dict[str, Any],
    ready: Set[str],
) -> Tuple[bool, List[str]]:
    """Cross-check prerequisites and planned target before appending a successful step."""
    errors: List[str] = []
    meta = (matrix.get("addons") or {}).get(name) or {}
    for req in meta.get("requires") or []:
        if req not in ready:
            errors.append(f"prerequisite {req} not ready for {name}")
    planned_version = planned.get("addon_version")
    target = meta.get("target")
    if planned_version != target:
        errors.append(f"{name}: planned version does not match matrix target")
    return len(errors) == 0, errors


def summarize_readiness(installed: Dict[str, Any], order: List[str]) -> Dict[str, Any]:
    """Build a compact readiness summary for checkpoint diagnostics."""
    summary: Dict[str, Any] = {}
    for name in order:
        meta = installed.get(name) or {}
        summary[name] = {
            "installed": meta.get("installed"),
            "status": normalize_status(meta.get("status")),
            "ready": is_addon_ready(meta.get("status")),
        }
    return summary
