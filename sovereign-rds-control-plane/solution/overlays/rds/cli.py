"""CLI operator interface for Sovereign RDS Control Plane."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional
from rds import config, evidence, repository, instance_manager, snapshot_manager, readiness


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Sovereign RDS Control Plane Operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_p = subparsers.add_parser("list")
    list_p.add_argument("--account", default="100000000000", help="Account ID")
    list_p.add_argument("--region", default="us-east-1", help="AWS Region")
    list_p.add_argument("--tenant", default=None, help="Tenant ID")

    health_p = subparsers.add_parser("health")
    health_p.add_argument("--account", default="100000000000", help="Account ID")
    health_p.add_argument("--region", default="us-east-1", help="AWS Region")

    snap_p = subparsers.add_parser("snapshot")
    snap_p.add_argument("--account", default="100000000000", help="Account ID")
    snap_p.add_argument("--region", default="us-east-1", help="AWS Region")
    snap_p.add_argument("--output-dir", default=None, help="Output directory")

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
    output_dir = Path(ns.output_dir) if getattr(ns, "output_dir", None) else Path(cfg.output_dir)

    if ns.command == "health":
        try:
            instances = await repo.list_instances(ns.account, ns.region)
            events = await repo.get_pending_outbox_events()
        except Exception:
            instances = []
            events = []
        health = readiness.ReadinessEvaluator.evaluate_readiness(
            instances, len(events), failing_probes_count=0
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "health.json").write_text(
            json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(health))
        return 0

    if ns.command == "list":
        tenant = getattr(ns, "tenant", None)
        instances = await repo.list_instances(ns.account, ns.region, tenant_id=tenant)
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
        try:
            instances = await repo.list_instances(ns.account, ns.region)
            events = await repo.get_pending_outbox_events()
        except Exception:
            instances = []
            events = []

        health = readiness.ReadinessEvaluator.evaluate_readiness(
            instances, len(events), failing_probes_count=0
        )
        report_data = {
            "status": health["status"],
            "total_instances": health["total_instances"],
            "available_instances": health["available_instances"],
            "active_replicas": sum(1 for i in instances if i.get("primary_instance_id")),
            "pending_events": len(events),
            "instances": instances,
        }
        digest = evidence.EvidencePublisher.publish_report(report_data, output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        with (output_dir / "instances.jsonl").open("w", encoding="utf-8") as fh:
            for inst in sorted(instances, key=lambda x: str(x.get("instance_id"))):
                fh.write(json.dumps(inst, sort_keys=True, default=str) + "\n")
        with (output_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
            for evt in events:
                fh.write(json.dumps(evt, sort_keys=True, default=str) + "\n")
        (output_dir / "health.json").write_text(
            json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        print(json.dumps({"status": health["status"], "report_digest": digest}))
        return 0

    print(json.dumps({"status": "READY"}))
    return 0


def run_cli(args: Optional[List[str]] = None) -> int:
    """Run CLI operator command synchronously."""
    ns = parse_args(args)
    return asyncio.run(execute_cli(ns))
