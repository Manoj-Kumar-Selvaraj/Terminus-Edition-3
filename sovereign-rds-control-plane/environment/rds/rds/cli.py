"""CLI operator interface for Sovereign RDS Control Plane."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional
from rds import config, evidence, repository, instance_manager, snapshot_manager

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Sovereign RDS Control Plane Operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subparsers.add_parser("list")
    list_p.add_argument("--account", default="100000000000", help="Account ID")
    list_p.add_argument("--region", default="us-east-1", help="AWS Region")

    # health
    health_p = subparsers.add_parser("health")

    # snapshot
    snap_p = subparsers.add_parser("snapshot")
    snap_p.add_argument("--account", default="100000000000", help="Account ID")
    snap_p.add_argument("--region", default="us-east-1", help="AWS Region")

    # create-snapshot
    create_snap_p = subparsers.add_parser("create-snapshot")
    create_snap_p.add_argument("--instance-id", required=True, help="Instance ID")
    create_snap_p.add_argument("--snapshot-id", required=True, help="Snapshot ID")

    # promote
    promote_p = subparsers.add_parser("promote")
    promote_p.add_argument("--replica-id", required=True, help="Replica Instance ID")

    # failover
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

    if ns.command == "health":
        print(json.dumps({"status": "READY"}))
        return 0

    if ns.command == "list":
        instances = await repo.list_instances(ns.account, ns.region)
        print(json.dumps({"instances": instances, "status": "READY"}, default=str))
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
        report_data = {
            "status": "READY",
            "total_instances": len(instances),
            "available_instances": sum(1 for i in instances if i.get("status") == "AVAILABLE"),
            "active_replicas": sum(1 for i in instances if i.get("primary_instance_id")),
            "pending_events": 0,
            "instances": instances
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
