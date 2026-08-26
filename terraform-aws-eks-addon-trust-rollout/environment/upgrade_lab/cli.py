"""CLI runner for the EKS Add-on Trust Upgrade Lab."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from upgrade_lab.config import load_config
from upgrade_lab.rollout_coordinator import execute_rollout


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EKS Add-on Trust Rollout Operator"
    )
    parser.add_argument(
        "--data-dir", help="Override path to datasets directory"
    )
    parser.add_argument(
        "--var-dir", help="Override path to var/upgrade directory"
    )
    parser.add_argument(
        "--output-dir", help="Override path to output directory"
    )
    parser.add_argument(
        "--k8s-dir", help="Override path to k8s manifests directory"
    )
    parser.add_argument(
        "--fail-addon", help="Simulate readiness failure for specified add-on"
    )
    return parser.parse_args(args)


def run_cli(args: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint execution."""
    ns = parse_args(args)
    cfg = load_config()

    if ns.data_dir:
        cfg.data_dir = type(cfg.data_dir)(ns.data_dir)
    if ns.var_dir:
        cfg.var_dir = type(cfg.var_dir)(ns.var_dir)
    if ns.output_dir:
        cfg.output_dir = type(cfg.output_dir)(ns.output_dir)
    if ns.k8s_dir:
        cfg.k8s_dir = type(cfg.k8s_dir)(ns.k8s_dir)

    plan_file = cfg.plan_json_path
    if not plan_file.is_file():
        sys.stderr.write(f"Plan file missing at {plan_file}\n")
        return 1

    try:
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.stderr.write(f"Failed to read plan JSON: {exc}\n")
        return 1

    report = execute_rollout(plan, cfg, fail_addon=ns.fail_addon)
    print(json.dumps({"status": report["status"], "digest": report["report_digest"]}))
    return 0 if report["status"] == "READY" else 1
