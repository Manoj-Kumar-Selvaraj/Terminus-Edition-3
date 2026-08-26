"""CLI operator interface for Sovereign RDS Control Plane."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from rds import config, evidence, repository, instance_manager, snapshot_manager
from rds.readiness import ReadinessEvaluator
from rds.audit_metrics import AuditMetricsEngine
from rds.coverage_analyzer import CoverageAnalyzer
from rds.disaster_recovery_evaluator import DisasterRecoveryEvaluator
from rds.authorization import AuthorizationEngine
from rds.maintenance_scheduler import MaintenanceWindowScheduler


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Sovereign RDS Control Plane Operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_p = subparsers.add_parser("list")
    list_p.add_argument("--account", default="100000000000", help="Account ID")
    list_p.add_argument("--region", default="us-east-1", help="AWS Region")
    list_p.add_argument("--tenant", default="tenant-01", help="Tenant ID")

    health_p = subparsers.add_parser("health")

    snap_p = subparsers.add_parser("snapshot")
    snap_p.add_argument("--account", default="100000000000", help="Account ID")
    snap_p.add_argument("--region", default="us-east-1", help="AWS Region")
    snap_p.add_argument("--tenant", default="tenant-01", help="Tenant ID")

    create_snap_p = subparsers.add_parser("create-snapshot")
    create_snap_p.add_argument("--instance-id", required=True, help="Instance ID")
    create_snap_p.add_argument("--snapshot-id", required=True, help="Snapshot ID")

    promote_p = subparsers.add_parser("promote")
    promote_p.add_argument("--replica-id", required=True, help="Replica Instance ID")

    failover_p = subparsers.add_parser("failover")
    failover_p.add_argument("--instance-id", required=True, help="Multi-AZ Instance ID")
    failover_p.add_argument("--worker-id", default="cli-operator", help="Worker ID")

    return parser.parse_args(args)


async def execute_cli(ns: argparse.Namespace) -> int:
    """Execute CLI commands with repository and manager integration."""
    cfg = config.load_config()
    repo = repository.RDSRepository()
    mgr = instance_manager.InstanceManager(repo)
    snap_mgr = snapshot_manager.SnapshotManager()
    audit = AuditMetricsEngine()
    coverage = CoverageAnalyzer()
    dr = DisasterRecoveryEvaluator()
    maintenance = MaintenanceWindowScheduler()

    if ns.command == "health":
        instances = await repo.list_instances("100000000000", "us-east-1")
        pending = 0
        if hasattr(repo, "get_pending_outbox_events"):
            try:
                pending = len(await repo.get_pending_outbox_events())
            except Exception:
                pending = 0
        ready = ReadinessEvaluator.evaluate_readiness(instances, pending, 0)
        print(json.dumps({
            "status": ready.get("status", "READY"),
            "readiness": ready,
            "sla": audit.calculate_availability_sla(instances),
            "maintenance_window_open": maintenance.is_in_maintenance_window(),
        }, default=str))
        return 0

    if ns.command == "list":
        instances = await repo.list_instances(ns.account, ns.region)
        filtered = AuthorizationEngine.enforce_tenant_isolation(
            instances, ns.account, ns.region, ns.tenant
        )
        print(json.dumps({
            "instances": filtered,
            "status": "READY",
            "sla": audit.calculate_availability_sla(filtered),
        }, default=str))
        return 0

    if ns.command == "create-snapshot":
        inst = await mgr.get_instance(ns.instance_id)
        snap = snap_mgr.create_snapshot(inst, ns.snapshot_id)
        await repo.create_snapshot_record(snap)
        print(json.dumps({"snapshot": snap, "status": "COMPLETED"}, default=str))
        return 0

    if ns.command == "promote":
        promoted = await mgr.promote_read_replica(ns.replica_id)
        print(json.dumps({"instance": promoted, "status": "PROMOTED"}, default=str))
        return 0

    if ns.command == "failover":
        res = await mgr.execute_failover(ns.instance_id, ns.worker_id)
        print(json.dumps({"instance": res, "status": "FAILOVER_COMPLETED"}, default=str))
        return 0

    if ns.command == "snapshot":
        instances = await repo.list_instances(ns.account, ns.region)
        filtered = AuthorizationEngine.enforce_tenant_isolation(
            instances, ns.account, ns.region, getattr(ns, "tenant", "tenant-01")
        )
        replicas = [i for i in filtered if i.get("primary_instance_id")]
        pending = 0
        if hasattr(repo, "get_pending_outbox_events"):
            try:
                pending = len(await repo.get_pending_outbox_events())
            except Exception:
                pending = 0
        report_data = {
            "status": "READY",
            "total_instances": len(filtered),
            "available_instances": sum(1 for i in filtered if i.get("status") == "AVAILABLE"),
            "active_replicas": len(replicas),
            "pending_events": pending,
            "instances": filtered,
            "dr_summary": dr.evaluate_dr_readiness(
                filtered[0] if filtered else {"status": "FAILED"}, replicas
            ) if filtered else {"dr_ready": False},
            "replication_telemetry": audit.calculate_replication_telemetry(replicas),
            "wal_coverage": coverage.analyze_wal_coverage([]),
        }
        digest = evidence.EvidencePublisher.publish_report(report_data, Path(cfg.output_dir))
        print(json.dumps({"status": "READY", "report_digest": digest}))
        return 0

    print(json.dumps({"status": "READY"}))
    return 0


def run_cli(args: Optional[List[str]] = None) -> int:
    """Run CLI operator command synchronously."""
    ns = parse_args(args)
    return asyncio.run(execute_cli(ns))
