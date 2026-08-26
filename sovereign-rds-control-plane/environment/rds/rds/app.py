"""FastAPI REST API server application for Sovereign RDS Control Plane."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from rds import config, repository, instance_manager, snapshot_manager, parameter_group_orchestrator, pitr_engine, evidence

class CreateDBInstanceRequest(BaseModel):
    instance_id: str
    tenant_id: str = "tenant-01"
    account_id: str = "100000000000"
    region: str = "us-east-1"
    db_instance_class: str = "db.m6i.xlarge"
    allocated_storage_gb: int = 100
    engine: str = "postgres"
    deletion_protection: bool = True

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

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(title="Sovereign RDS Control Plane API")

    cfg = config.load_config()
    repo = repository.RDSRepository()
    mgr = instance_manager.InstanceManager(repo)
    snap_mgr = snapshot_manager.SnapshotManager()
    param_orch = parameter_group_orchestrator.ParameterGroupOrchestrator()

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/api/v1/instances")
    async def list_instances(account_id: str = "100000000000", region: str = "us-east-1"):
        """List DBInstances."""
        instances = await repo.list_instances(account_id, region)
        return {"instances": instances, "status": "AVAILABLE"}

    @app.get("/api/v1/instances/{instance_id}")
    async def get_instance(instance_id: str):
        """Get DBInstance details."""
        try:
            inst = await mgr.get_instance(instance_id)
            return {"instance": inst}
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/v1/instances/create")
    async def create_instance(req: CreateDBInstanceRequest):
        """Create new DBInstance."""
        try:
            res = await mgr.create_instance(req.model_dump())
            return {"instance": res, "status": "CREATING"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/instances/modify")
    async def modify_instance(req: ModifyDBInstanceRequest):
        """Modify DBInstance."""
        try:
            res = await mgr.modify_instance(req.instance_id, req.model_dump(exclude_unset=True))
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
            snaps = await repo.execute_query("SELECT * FROM db_snapshots WHERE snapshot_id = %s", (req.source_snapshot_id,))
            if not snaps:
                raise HTTPException(status_code=404, detail="Source snapshot not found")
            copied = snap_mgr.copy_snapshot(snaps[0], req.target_snapshot_id, req.target_region)
            return {"snapshot": copied, "status": "COMPLETED"}
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
            return {"restore_plan": plan, "status": "PLANNED"}
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

    return app
