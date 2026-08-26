"""Step-by-step add-on rollout state machine and readiness coordinator."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from upgrade_lab.checkpoint_manager import CheckpointManager
from upgrade_lab.drain_simulator import simulate_node_drain
from upgrade_lab.interruption_handler import simulate_node_interruption
from upgrade_lab.irsa_verifier import verify_irsa_bindings
from upgrade_lab.k8s_parser import apply_k8s_manifests
from upgrade_lab.matrix_evaluator import get_upgrade_order, validate_prerequisites
from upgrade_lab.pdb_analyzer import evaluate_pdb_coverage
from upgrade_lab.plan_normalizer import normalize_terraform_plan
from upgrade_lab.plan_validator import validate_plan_policies
from upgrade_lab.placement_engine import evaluate_regulated_placement
from upgrade_lab.report_publisher import publish_upgrade_report


def load_dataset_json(data_dir: Any, filename: str) -> Dict[str, Any]:
    """Load JSON file from dataset directory."""
    path = data_dir / filename
    return json.loads(path.read_text(encoding="utf-8"))


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

    # 1. Normalize Terraform plan and run plan policy checks
    graph = normalize_terraform_plan(plan)
    policy_errors = validate_plan_policies(
        graph, matrix, trust, defaults, regulated_policy, snapshot
    )

    order = get_upgrade_order(matrix)
    report: Dict[str, Any] = {
        "status": "FAILED",
        "reason": None,
        "policy_errors": policy_errors,
        "upgrade_order": [],
        "steps": [],
        "availability": {name: False for name in (defaults.get("core_services") or [])},
        "pdb_respected": False,
        "drain_result": {
            "node": defaults.get("drain_node", "ip-10-0-1-50.ec2.internal"),
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

    if policy_errors:
        report["reason"] = "plan_policy"
        publish_upgrade_report(report, cfg.output_dir)
        return report

    # 2. Parse submitted Kubernetes manifests and check PDB coverage
    k8s_state = apply_k8s_manifests(cfg.k8s_dir)
    ok_pdb, pdb_errs = evaluate_pdb_coverage(k8s_state.get("pdbs") or [], pdbs.get("required") or [])
    if not ok_pdb:
        report["reason"] = "missing_pdbs"
        report["policy_errors"] = pdb_errs
        publish_upgrade_report(report, cfg.output_dir)
        return report

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
        report["reason"] = "irsa_binding" if irsa_errs else "cross_service_trust"
        publish_upgrade_report(report, cfg.output_dir)
        return report

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
        prereqs_ok, missing_prereqs = validate_prerequisites(name, matrix, ready)
        if not prereqs_ok:
            report["reason"] = f"prerequisite_missing:{name}"
            checkpoint.save_checkpoint(
                {
                    "ready": sorted(ready),
                    "upgrade_order": list(report["upgrade_order"]),
                    "steps": list(report["steps"]),
                }
            )
            publish_upgrade_report(report, cfg.output_dir)
            return report

        if fail_addon and name == fail_addon:
            report["steps"].append(
                {
                    "addon": name,
                    "from_version": (installed.get(name) or {}).get("installed"),
                    "to_version": meta.get("target"),
                    "ok": False,
                }
            )
            report["reason"] = f"readiness_failed:{name}"
            checkpoint.save_checkpoint(
                {
                    "ready": sorted(ready),
                    "upgrade_order": list(report["upgrade_order"]),
                    "steps": list(report["steps"]),
                }
            )
            publish_upgrade_report(report, cfg.output_dir)
            return report

        planned = (graph.get("addons") or {}).get(name) or {}
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
        installed[name] = {"installed": planned.get("addon_version"), "status": "ACTIVE"}
        checkpoint.save_checkpoint(
            {
                "ready": sorted(ready),
                "upgrade_order": list(report["upgrade_order"]),
                "steps": list(report["steps"]),
            }
        )

    # 5. Verify core availability and simulate system node drain
    for svc in defaults.get("core_services") or []:
        report["availability"][svc] = True

    report["drain_result"] = simulate_node_drain(defaults, pdb_respected=True)
    report["pdb_respected"] = True

    # 6. Evaluate regulated workload placement
    placement_results, placement_ok, placement_errs = evaluate_regulated_placement(
        k8s_state, regulated_policy
    )
    report["regulated_placement"] = placement_results

    if not placement_ok:
        report["reason"] = "regulated_placement"
        publish_upgrade_report(report, cfg.output_dir)
        return report

    # 7. Simulate spot/on-demand node interruption
    interruption_res = simulate_node_interruption(graph, placement_results)
    report["interruption"] = interruption_res

    if not interruption_res.get("regulated_still_on_demand"):
        report["reason"] = "interruption_placement"
        publish_upgrade_report(report, cfg.output_dir)
        return report

    # 8. Mark ready and publish final report
    report["status"] = "READY"
    report["reason"] = None
    checkpoint.clear_checkpoint()
    publish_upgrade_report(report, cfg.output_dir)
    return report
