"""Canonical JSON serialization and SHA-256 digest calculations."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_text(text: str) -> str:
    """Compute SHA-256 digest over UTF-8 text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_dump(payload: Any) -> str:
    """Serialize payload as compact sorted-keys JSON string."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_stable_digest(payload: Any) -> str:
    """Compute SHA-256 digest over canonical JSON representation."""
    return sha256_text(canonical_json_dump(payload))


def compute_report_digest(report: dict[str, Any]) -> str:
    """Compute canonical SHA-256 digest over the stable subset of an upgrade report."""
    stable_subset = {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "policy_errors": sorted(report.get("policy_errors") or []),
        "upgrade_order": report.get("upgrade_order") or [],
        "steps": report.get("steps") or [],
        "availability": report.get("availability") or {},
        "pdb_respected": report.get("pdb_respected", False),
        "drain_result": report.get("drain_result") or {},
        "irsa_bindings": {
            k: {"subject": v.get("subject"), "ok": v.get("ok")}
            for k, v in sorted((report.get("irsa_bindings") or {}).items())
        },
        "cross_service_denied": report.get("cross_service_denied", False),
        "regulated_placement": report.get("regulated_placement") or {},
        "interruption": report.get("interruption") or {},
    }
    return compute_stable_digest(stable_subset)
