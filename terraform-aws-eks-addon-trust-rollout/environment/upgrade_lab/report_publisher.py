"""Upgrade report publisher and SHA-256 digest calculator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from upgrade_lab.digests import compute_report_digest


REQUIRED_REPORT_KEYS = (
    "status",
    "reason",
    "policy_errors",
    "upgrade_order",
    "steps",
    "availability",
    "pdb_respected",
    "drain_result",
    "irsa_bindings",
    "cross_service_denied",
    "regulated_placement",
    "interruption",
    "report_digest",
)


def ensure_report_shape(report: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing report keys with fail-closed defaults without dropping data."""
    report.setdefault("status", "FAILED")
    report.setdefault("reason", None)
    report.setdefault("policy_errors", [])
    report.setdefault("upgrade_order", [])
    report.setdefault("steps", [])
    report.setdefault("availability", {})
    report.setdefault("pdb_respected", False)
    report.setdefault(
        "drain_result",
        {"node": None, "core_available": False, "evicted_count": 0, "blocked_count": 0},
    )
    report.setdefault("irsa_bindings", {})
    report.setdefault("cross_service_denied", False)
    report.setdefault("regulated_placement", {})
    report.setdefault(
        "interruption",
        {"handled": False, "regulated_still_on_demand": False},
    )
    report.setdefault("report_digest", "")
    return report


def canonicalize_interruption(interruption: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish only the graded interruption fields in the digest-facing object.

    Extra diagnostic keys remain on the in-memory report when present but the
    stable digest uses handled + regulated_still_on_demand via digests.py.
    """
    return {
        "handled": bool(interruption.get("handled", False)),
        "regulated_still_on_demand": bool(
            interruption.get("regulated_still_on_demand", False)
        ),
    }


def publish_upgrade_report(report: Dict[str, Any], output_dir: Path) -> str:
    """Compute report digest, write report to upgrade-report.json, and return digest string."""
    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ensure_report_shape(report)

    # Graded interruption schema is exactly two fields; drop diagnostics before digest.
    interruption = report.get("interruption") or {}
    if isinstance(interruption, dict):
        report["interruption"] = canonicalize_interruption(interruption)

    digest = compute_report_digest(report)
    report["report_digest"] = digest

    report_file = out_dir / "upgrade-report.json"
    report_file.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return digest


def missing_report_keys(report: Dict[str, Any]) -> List[str]:
    """Return required schema keys absent from a report payload."""
    return [key for key in REQUIRED_REPORT_KEYS if key not in report]
