"""Step-by-step add-on rollout state machine and readiness coordinator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from upgrade_lab.checkpoint_manager import CheckpointManager
from upgrade_lab.drain_simulator import simulate_node_drain
from upgrade_lab.interruption_handler import simulate_node_interruption
from upgrade_lab.irsa_verifier import verify_irsa_bindings
from upgrade_lab.k8s_parser import apply_k8s_manifests
from upgrade_lab.matrix_evaluator import (
    get_upgrade_order,
    readiness_gate,
    validate_matrix_integrity,
)
from upgrade_lab.addon_readiness import poll_addon_readiness, verify_step_completion
from upgrade_lab.pdb_analyzer import evaluate_pdb_coverage
from upgrade_lab.plan_normalizer import normalize_terraform_plan
from upgrade_lab.plan_validator import validate_plan_policies
from upgrade_lab.placement_engine import evaluate_regulated_placement
from upgrade_lab.report_publisher import publish_upgrade_report


def load_dataset_json(data_dir: Any, filename: str) -> Any:
    """Load JSON file from dataset directory."""
    path = Path(data_dir) / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _empty_report(defaults: Dict[str, Any], policy_errors: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "status": "FAILED",
        "reason": None,
        "policy_errors": list(policy_errors or []),
        "upgrade_order": [],
        "steps": [],
        "availability": {name: False for name in (defaults.get("core_services") or [])},
        "pdb_respected": False,
        "drain_result": {
            "node": defaults.get("drain_node", "ip-10-0-1-10.ec2.internal"),
            "core_available": False,
            "evicted_count": 0,
            "blocked_count": 0,
        },
        "irsa_bindings": {},
        "cross_service_denied": False,
        "regulated_placement": {},
        "interruption": {"handled": False, "regulated_still_on_demand": False},
        "report_digest": "",
    }


def _publish(report: Dict[str, Any], cfg: Any) -> Dict[str, Any]:
    publish_upgrade_report(report, cfg.output_dir)
    return report


def execute_rollout(
    plan: Dict[str, Any],
    cfg: Any,
    *,
    fail_addon: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete EKS add-on trust rollout pipeline and generate upgrade readiness report."""
    data_dir = cfg.data_dir
    snapshot = load_dataset_json(data_dir, "cluster_snapshot.json")
    matrix = load_dataset_json(data_dir, "compatibility_matrix.json")
    trust = load_dataset_json(data_dir, "trust_observations.json")
    pdbs = load_dataset_json(data_dir, "pdbs.json")
    regulated_policy = load_dataset_json(data_dir, "regulated_policy.json")
    defaults = load_dataset_json(data_dir, "defaults.json")

    report = _empty_report(defaults)

    matrix_ok, matrix_errs = validate_matrix_integrity(matrix)
    if not matrix_ok:
        report["reason"] = "plan_policy"
        report["policy_errors"] = matrix_errs
        return _publish(report, cfg)

    # 1. Normalize Terraform plan and run plan policy checks
    graph = normalize_terraform_plan(plan)
    policy_errors = validate_plan_policies(
        graph, matrix, trust, defaults, regulated_policy, snapshot
    )
    report["policy_errors"] = policy_errors

    order = get_upgrade_order(matrix)
    if policy_errors:
        report["reason"] = "plan_policy"
        return _publish(report, cfg)

    # 2. Parse submitted Kubernetes manifests and check PDB coverage
    k8s_state = apply_k8s_manifests(cfg.k8s_dir)
    ok_pdb, pdb_errs = evaluate_pdb_coverage(
        k8s_state.get("pdbs") or [], pdbs.get("required") or []
    )
    if not ok_pdb:
        report["reason"] = "missing_pdbs"
        report["policy_errors"] = pdb_errs
        return _publish(report, cfg)

    # 3. Verify IRSA bindings and cross-service trust isolation
    bindings, irsa_ok, irsa_errs = verify_irsa_bindings(
        graph.get("roles") or {},
        k8s_state.get("service_accounts") or [],
        trust,
        defaults,
    )
    report["irsa_bindings"] = bindings
    report["cross_service_denied"] = irsa_ok

    if not irsa_ok:
        # Prefer specific binding failures over cross-service when both present.
        if any("binding failed" in e or "missing" in e.lower() for e in irsa_errs):
            report["reason"] = "irsa_binding"
        else:
            report["reason"] = "cross_service_trust"
        return _publish(report, cfg)

    # 4. Simulate add-on rollout step-by-step in prerequisite order
    checkpoint = CheckpointManager(cfg.checkpoint_path)
    prior = checkpoint.load_checkpoint() or {}
    ready: set[str] = set(prior.get("ready") or [])
    report["upgrade_order"] = list(prior.get("upgrade_order") or [])
    report["steps"] = list(prior.get("steps") or [])
    installed = dict(snapshot.get("addons") or {})
    for cname, cmeta in (snapshot.get("controllers") or {}).items():
        installed[cname] = cmeta
    for done in report["upgrade_order"]:
        planned_done = (graph.get("addons") or {}).get(done) or {}
        installed[done] = {
            "installed": planned_done.get("addon_version"),
            "status": "ACTIVE",
        }

    for name in order:
        if name in ready:
            continue
        meta = (matrix.get("addons") or {})[name]
        gate_ok, gate_reason = readiness_gate(
            name, matrix=matrix, ready=ready, fail_addon=fail_addon
        )
        if not gate_ok:
            if gate_reason and gate_reason.startswith("readiness_failed:"):
                report["steps"].append(
                    {
                        "addon": name,
                        "from_version": (installed.get(name) or {}).get("installed"),
                        "to_version": meta.get("target"),
                        "ok": False,
                    }
                )
            report["reason"] = gate_reason
            checkpoint.append_step_and_save(
                ready=ready,
                upgrade_order=report["upgrade_order"],
                steps=report["steps"],
            )
            return _publish(report, cfg)

        planned = (graph.get("addons") or {}).get(name) or {}
        step_ok, _step_errs = verify_step_completion(
            name, matrix=matrix, planned=planned, ready=ready
        )
        # Prior snapshot may be DEGRADED; readiness after plan application is version-gated.
        ready_ok, _ready_detail = poll_addon_readiness(
            name,
            installed={"status": "ACTIVE", "installed": planned.get("addon_version")},
            planned_version=planned.get("addon_version"),
            target_version=meta.get("target"),
        )
        if not step_ok or not ready_ok:
            report["steps"].append(
                {
                    "addon": name,
                    "from_version": (installed.get(name) or {}).get("installed"),
                    "to_version": planned.get("addon_version") or meta.get("target"),
                    "ok": False,
                }
            )
            report["reason"] = f"readiness_failed:{name}"
            checkpoint.append_step_and_save(
                ready=ready,
                upgrade_order=report["upgrade_order"],
                steps=report["steps"],
            )
            return _publish(report, cfg)

        report["steps"].append(
            {
                "addon": name,
                "from_version": (installed.get(name) or {}).get("installed"),
                "to_version": planned.get("addon_version"),
                "ok": True,
            }
        )
        report["upgrade_order"].append(name)
        ready.add(name)
        installed[name] = {
            "installed": planned.get("addon_version"),
            "status": "ACTIVE",
        }
        checkpoint.append_step_and_save(
            ready=ready,
            upgrade_order=report["upgrade_order"],
            steps=report["steps"],
        )

    # 5. Simulate system node drain from PDB thresholds + replica capacity
    drain_result, availability, pdb_respected = simulate_node_drain(
        defaults,
        k8s_state=k8s_state,
        required_pdbs=pdbs.get("required") or [],
        pdb_coverage_ok=True,
    )
    report["drain_result"] = drain_result
    report["availability"] = availability
    report["pdb_respected"] = pdb_respected

    if not pdb_respected or not drain_result.get("core_available"):
        report["reason"] = "drain_availability"
        return _publish(report, cfg)

    # 6. Evaluate regulated workload placement
    placement_results, placement_ok, placement_errs = evaluate_regulated_placement(
        k8s_state, regulated_policy
    )
    report["regulated_placement"] = placement_results

    if not placement_ok:
        report["reason"] = "regulated_placement"
        return _publish(report, cfg)

    # 7. Simulate spot/on-demand node interruption from curated events
    events_path = cfg.resolve_interruption_file(defaults) if hasattr(cfg, "resolve_interruption_file") else (
        Path(cfg.data_dir) / defaults.get("interruption_events_file", "interruption_events.json")
    )
    interruption_res = simulate_node_interruption(
        graph,
        placement_results,
        events_path=events_path,
        regulated_policy=regulated_policy,
    )
    report["interruption"] = {
        "handled": bool(interruption_res.get("handled")),
        "regulated_still_on_demand": bool(
            interruption_res.get("regulated_still_on_demand")
        ),
    }

    if not interruption_res.get("regulated_still_on_demand"):
        report["reason"] = "interruption_placement"
        return _publish(report, cfg)

    # 8. Mark ready and publish final report
    report["status"] = "READY"
    report["reason"] = None
    checkpoint.clear_checkpoint()
    return _publish(report, cfg)
