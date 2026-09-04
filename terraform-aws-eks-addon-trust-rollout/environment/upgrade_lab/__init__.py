"""EKS Add-on Trust Upgrade Lab Package."""
from __future__ import annotations

from typing import Any, Dict, Optional

from upgrade_lab.app import run_rollout_app
from upgrade_lab.config import LabConfig, load_config
from upgrade_lab.digests import compute_report_digest, canonical_json_dump
from upgrade_lab.plan_normalizer import normalize_terraform_plan
from upgrade_lab.plan_validator import validate_plan_policies
from upgrade_lab.matrix_evaluator import get_upgrade_order, validate_prerequisites
from upgrade_lab.irsa_verifier import verify_irsa_bindings
from upgrade_lab.pdb_analyzer import evaluate_pdb_coverage
from upgrade_lab.k8s_parser import apply_k8s_manifests
from upgrade_lab.placement_engine import evaluate_regulated_placement
from upgrade_lab.drain_simulator import simulate_node_drain
from upgrade_lab.interruption_handler import simulate_node_interruption
from upgrade_lab.report_publisher import publish_upgrade_report
from upgrade_lab.addon_readiness import poll_addon_readiness, verify_step_completion


def run_rollout(
    plan: Dict[str, Any],
    *,
    fail_addon: Optional[str] = None,
    k8s_dir: Any = None,
) -> Dict[str, Any]:
    """Top-level rollout entrypoint maintaining backward compatibility with legacy calls."""
    cfg = load_config()
    if k8s_dir:
        cfg.k8s_dir = type(cfg.k8s_dir)(k8s_dir)
    return run_rollout_app(plan, cfg, fail_addon=fail_addon)


__all__ = [
    "run_rollout",
    "run_rollout_app",
    "LabConfig",
    "load_config",
    "compute_report_digest",
    "canonical_json_dump",
    "normalize_terraform_plan",
    "validate_plan_policies",
    "get_upgrade_order",
    "validate_prerequisites",
    "verify_irsa_bindings",
    "evaluate_pdb_coverage",
    "apply_k8s_manifests",
    "evaluate_regulated_placement",
    "simulate_node_drain",
    "simulate_node_interruption",
    "publish_upgrade_report",
    "poll_addon_readiness",
    "verify_step_completion",
]
