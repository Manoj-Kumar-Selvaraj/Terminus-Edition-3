"""FastAPI REST API server application for Sovereign RDS Control Plane."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from rds import (
    config,
    repository,
    instance_manager,
    snapshot_manager,
    parameter_group_orchestrator,
    pitr_engine,
    evidence,
)
from rds.authorization import AuthorizationEngine
from rds.readiness import ReadinessEvaluator
from rds.audit_metrics import AuditMetricsEngine
from rds.coverage_analyzer import CoverageAnalyzer
from rds.disaster_recovery_evaluator import DisasterRecoveryEvaluator
from rds.maintenance_scheduler import MaintenanceWindowScheduler
from rds.kms_encryption_manager import KMSEncryptionManager
from rds.instance_scaling_policy import InstanceScalingPolicy
from rds.connection_pool_monitor import ConnectionPoolMonitor


class CreateDBInstanceRequest(BaseModel):
    instance_id: str
    tenant_id: str = "tenant-01"
    account_id: str = "100000000000"
    region: str = "us-east-1"
    db_instance_class: str = "db.m6i.xlarge"
    allocated_storage_gb: int = 100
    engine: str = "postgres"
    deletion_protection: bool = True
    kms_key_id: Optional[str] = None


class ModifyDBInstanceRequest(BaseModel):
    instance_id: str
    allocated_storage_gb: Optional[int] = None
    db_instance_class: Optional[str] = None
    apply_immediately: bool = False


class DeleteDBInstanceRequest(BaseModel):
    instance_id: str
    final_snapshot_id: Optional[str] = None


class CreateSnapshotRequest(BaseModel):
    instance_id: str
    snapshot_id: str


class CopySnapshotRequest(BaseModel):
    source_snapshot_id: str
    target_snapshot_id: str
    target_region: str = "us-west-2"


class RestorePITRRequest(BaseModel):
    source_instance_id: str
    target_instance_id: str
    target_timestamp_iso: str


class ModifyParameterGroupRequest(BaseModel):
    parameter_group_name: str
    parameters: Dict[str, str]


class ScheduleMaintenanceRequest(BaseModel):
    instance_id: str
    task_type: str = "minor-version-upgrade"
    description: str = "Scheduled maintenance"
    apply_immediately: bool = False


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(title="Sovereign RDS Control Plane API")

    cfg = config.load_config()
    repo = repository.RDSRepository()
    mgr = instance_manager.InstanceManager(repo)
    snap_mgr = snapshot_manager.SnapshotManager()
    param_orch = parameter_group_orchestrator.ParameterGroupOrchestrator()
    audit = AuditMetricsEngine()
    coverage = CoverageAnalyzer()
    dr = DisasterRecoveryEvaluator()
    maintenance = MaintenanceWindowScheduler()
    scaling = InstanceScalingPolicy()
    pool_monitor = ConnectionPoolMonitor()

    @app.get("/health")
    async def health():
        """Health check endpoint with readiness and pool saturation."""
        instances = await repo.list_instances("100000000000", "us-east-1")
        pending = 0
        if hasattr(repo, "get_pending_outbox_events"):
            try:
                pending = len(await repo.get_pending_outbox_events())
            except Exception:
                pending = 0
        pool = pool_monitor.evaluate_pool_saturation(active_connections=12, max_connections=100)
        ready = ReadinessEvaluator.evaluate_readiness(instances, pending, 0)
        return {
            "status": ready.get("status", "healthy").lower(),
            "readiness": ready,
            "pool": pool,
        }

    @app.get("/api/v1/instances")
    async def list_instances(
        account_id: str = "100000000000",
        region: str = "us-east-1",
        tenant_id: str = Header(default="tenant-01", alias="X-Tenant-Id"),
    ):
        """List DBInstances with multi-tenant projection."""
        instances = await repo.list_instances(account_id, region)
        filtered = AuthorizationEngine.enforce_tenant_isolation(
            instances, account_id, region, tenant_id
        )
        sla = audit.calculate_availability_sla(filtered)
        return {"instances": filtered, "status": "AVAILABLE", "sla": sla}

    @app.get("/api/v1/instances/{instance_id}")
    async def get_instance(
        instance_id: str,
        account_id: str = "100000000000",
        region: str = "us-east-1",
        tenant_id: str = Header(default="tenant-01", alias="X-Tenant-Id"),
    ):
        """Get DBInstance details."""
        try:
            inst = await mgr.get_instance(instance_id)
            AuthorizationEngine.authorize_single_instance(inst, account_id, region, tenant_id)
            return {"instance": inst}
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/v1/instances/create")
    async def create_instance(req: CreateDBInstanceRequest):
        """Create new DBInstance."""
        try:
            payload = req.model_dump()
            if payload.get("kms_key_id"):
                KMSEncryptionManager.validate_kms_key_authority(payload["kms_key_id"])
            res = await mgr.create_instance(payload)
            audit.record_audit_event(
                "instance.create", "api", "db-instance", req.instance_id, "CREATED"
            )
            return {"instance": res, "status": "CREATING"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/modify")
    async def modify_instance(req: ModifyDBInstanceRequest):
        """Modify DBInstance."""
        try:
            mods = req.model_dump(exclude_unset=True)
            if "allocated_storage_gb" in mods:
                should_scale, suggested, reason = scaling.evaluate_storage_autoscale(
                    int(mods["allocated_storage_gb"]),
                    free_storage_space_bytes=5 * 1024 * 1024 * 1024,
                )
                mods["autoscale_hint"] = {"should_scale": should_scale, "suggested": suggested, "reason": reason}
            res = await mgr.modify_instance(req.instance_id, mods)
            return {"instance": res, "status": "MODIFYING"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/reboot")
    async def reboot_instance(instance_id: str):
        """Reboot DBInstance."""
        try:
            res = await mgr.reboot_instance(instance_id)
            return {"instance": res, "status": "REBOOTING"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/promote")
    async def promote_replica(replica_id: str):
        """Promote read replica."""
        try:
            res = await mgr.promote_read_replica(replica_id)
            return {"instance": res, "status": "PROMOTED"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/failover")
    async def execute_failover(instance_id: str, worker_id: str = "worker-01"):
        """Execute Multi-AZ failover."""
        try:
            res = await mgr.execute_failover(instance_id, worker_id)
            return {"instance": res, "status": "FAILOVER_COMPLETED"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/delete")
    async def delete_instance(req: DeleteDBInstanceRequest):
        """Delete DBInstance."""
        try:
            res = await mgr.delete_instance(req.instance_id, req.final_snapshot_id)
            return res
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/snapshots/create")
    async def create_snapshot(req: CreateSnapshotRequest):
        """Create DBSnapshot."""
        try:
            inst = await mgr.get_instance(req.instance_id)
            snap = snap_mgr.create_snapshot(inst, req.snapshot_id)
            await repo.create_snapshot_record(snap)
            return {"snapshot": snap, "status": "COMPLETED"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/snapshots/copy")
    async def copy_snapshot(req: CopySnapshotRequest):
        """Copy DBSnapshot across regions."""
        try:
            snaps = await repo.execute_one(
                "SELECT * FROM db_snapshots WHERE snapshot_id = %s", (req.source_snapshot_id,)
            )
            if not snaps:
                raise HTTPException(status_code=404, detail="Source snapshot not found")
            copied = snap_mgr.copy_snapshot(snaps, req.target_snapshot_id, req.target_region)
            return {"snapshot": copied, "status": "COMPLETED"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/snapshots/pitr")
    async def restore_pitr(req: RestorePITRRequest):
        """Restore instance to Point-In-Time."""
        try:
            target_dt = datetime.fromisoformat(req.target_timestamp_iso)
            snaps = await repo.get_snapshots(req.source_instance_id)
            wals = await repo.get_wal_archives(req.source_instance_id)
            plan = pitr_engine.PITREngine.synthesize_restore_plan(
                req.source_instance_id, target_dt, snaps, wals
            )
            cov = coverage.analyze_wal_coverage(wals)
            return {"restore_plan": plan, "wal_coverage": cov, "status": "PLANNED"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/parametergroups/modify")
    async def modify_parameter_group(req: ModifyParameterGroupRequest):
        """Modify DBParameterGroup."""
        try:
            pg = await repo.get_parameter_group(req.parameter_group_name)
            if not pg:
                raise HTTPException(status_code=404, detail="Parameter group not found")
            updated, pending = param_orch.modify_parameter_group(pg, req.parameters)
            await repo.update_parameter_group(req.parameter_group_name, updated["parameters"])
            return {"parameter_group": updated, "pending_reboot_parameters": pending}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/maintenance/schedule")
    async def schedule_maintenance(req: ScheduleMaintenanceRequest):
        """Schedule instance maintenance within preferred window."""
        task = maintenance.schedule_maintenance_task(
            req.instance_id, req.task_type, req.description, req.apply_immediately
        )
        return {"task": task, "in_window": maintenance.is_in_maintenance_window()}

    @app.get("/api/v1/dr/evaluate/{instance_id}")
    async def evaluate_dr(instance_id: str):
        """Evaluate disaster-recovery readiness for an instance topology."""
        try:
            primary = await mgr.get_instance(instance_id)
            instances = await repo.list_instances(
                primary.get("account_id", "100000000000"),
                primary.get("region", "us-east-1"),
            )
            replicas = [i for i in instances if i.get("primary_instance_id") == instance_id]
            return {
                "dr": dr.evaluate_dr_readiness(primary, replicas),
                "rpo": dr.evaluate_rpo_compliance(
                    max((r.get("replication_lag_bytes") or 0) for r in replicas) if replicas else 0
                ),
                "replication": audit.calculate_replication_telemetry(replicas),
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app
