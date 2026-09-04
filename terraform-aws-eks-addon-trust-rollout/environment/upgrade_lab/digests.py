"""Canonical JSON serialization and SHA-256 digest calculations."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def sha256_text(text: str) -> str:
    """Compute SHA-256 digest over UTF-8 text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_dump(payload: Any) -> str:
    """Serialize payload as compact sorted-keys JSON string."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_stable_digest(payload: Any) -> str:
    """Compute SHA-256 digest over canonical JSON representation."""
    return sha256_text(canonical_json_dump(payload))


def stable_irsa_bindings(bindings: Any) -> Dict[str, Any]:
    """Reduce IRSA bindings to digest-stable subject/ok fields."""
    if not isinstance(bindings, dict):
        return {}
    stable: Dict[str, Any] = {}
    for key, value in sorted(bindings.items()):
        if not isinstance(value, dict):
            continue
        stable[str(key)] = {
            "subject": value.get("subject"),
            "ok": bool(value.get("ok")),
        }
    return stable


def stable_drain_result(drain: Any) -> Dict[str, Any]:
    """Reduce drain_result to the graded four-field schema."""
    if not isinstance(drain, dict):
        return {
            "node": None,
            "core_available": False,
            "evicted_count": 0,
            "blocked_count": 0,
        }
    return {
        "node": drain.get("node"),
        "core_available": bool(drain.get("core_available", False)),
        "evicted_count": int(drain.get("evicted_count") or 0),
        "blocked_count": int(drain.get("blocked_count") or 0),
    }


def stable_interruption(interruption: Any) -> Dict[str, Any]:
    """Reduce interruption payload to graded handled/on-demand fields."""
    if not isinstance(interruption, dict):
        return {"handled": False, "regulated_still_on_demand": False}
    return {
        "handled": bool(interruption.get("handled", False)),
        "regulated_still_on_demand": bool(
            interruption.get("regulated_still_on_demand", False)
        ),
    }


def build_stable_report_subset(report: dict[str, Any]) -> Dict[str, Any]:
    """Extract the stable semantic subset used for report digests."""
    return {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "policy_errors": sorted(report.get("policy_errors") or []),
        "upgrade_order": report.get("upgrade_order") or [],
        "steps": report.get("steps") or [],
        "availability": report.get("availability") or {},
        "pdb_respected": report.get("pdb_respected", False),
        "drain_result": stable_drain_result(report.get("drain_result")),
        "irsa_bindings": stable_irsa_bindings(report.get("irsa_bindings")),
        "cross_service_denied": report.get("cross_service_denied", False),
        "regulated_placement": report.get("regulated_placement") or {},
        "interruption": stable_interruption(report.get("interruption")),
    }


def compute_report_digest(report: dict[str, Any]) -> str:
    """Compute canonical SHA-256 digest over the stable subset of an upgrade report."""
    return compute_stable_digest(build_stable_report_subset(report))
