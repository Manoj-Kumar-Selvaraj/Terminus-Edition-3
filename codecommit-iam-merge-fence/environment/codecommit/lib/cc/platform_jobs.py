"""Scheduled platform jobs that exercise admin modules."""

from __future__ import annotations

from typing import Any

from cc import home
from cc.change_window import evaluate_refs
from cc.compliance_scanner import score_findings, write_compliance_report
from cc.drift_detector import full_drift_report, write_drift_report
from cc.notification_routing import routing_health, seed_default_routes
from cc.operator_workflows import export_platform_bundle, reconcile_ops, write_ops_snapshot
from cc.principal_graph import graph_export


def nightly() -> dict[str, Any]:
    seed_default_routes()
    return {
        "compliance": score_findings(),
        "drift": full_drift_report(),
        "graph": graph_export(),
        "routing": routing_health(),
        "ops": reconcile_ops(),
        "windows": evaluate_refs(["main", "release", "dev/alice"]),
        "compliance_path": str(write_compliance_report()),
        "drift_path": str(write_drift_report()),
        "ops_path": str(write_ops_snapshot()),
        "bundle_path": str(export_platform_bundle(home.var_dir() / "bundle.json")),
    }
