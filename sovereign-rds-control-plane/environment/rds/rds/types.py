"""Data models and type definitions for Sovereign RDS Control Plane."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DBInstance(BaseModel):
    """Database instance data model."""
    instance_id: str
    tenant_id: str
    account_id: str
    region: str
    engine: str = "postgres"
    engine_version: str = "16.2"
    db_instance_class: str = "db.m6i.xlarge"
    allocated_storage_gb: int = 100
    storage_type: str = "gp3"
    status: str = "AVAILABLE"
    deletion_protection: bool = True
    multi_az: bool = False
    publicly_accessible: bool = False
    master_username: str = "postgres"
    endpoint_address: Optional[str] = None
    endpoint_port: int = 5432
    parameter_group_name: str = "default.postgres16"
    pending_reboot_parameters: bool = False
    backup_retention_period: int = 7
    earliest_restorable_time: Optional[datetime] = None
    latest_restorable_time: Optional[datetime] = None
    primary_instance_id: Optional[str] = None
    replication_status: Optional[str] = None
    replication_lag_bytes: int = 0
    write_lease_owner: Optional[str] = None
    write_lease_expires_at: Optional[datetime] = None

class DBParameterGroup(BaseModel):
    """Database parameter group model."""
    parameter_group_name: str
    family: str = "postgres16"
    description: str = ""
    parameters_json: Dict[str, Any] = Field(default_factory=dict)

class ParameterDefinition(BaseModel):
    """Parameter definition model."""
    parameter_name: str
    family: str = "postgres16"
    apply_type: str = "dynamic"
    data_type: str = "string"
    allowed_values: Optional[str] = None
    default_value: str

class WALArchive(BaseModel):
    """WAL archive segment model."""
    instance_id: str
    timeline_id: int = 1
    sequence_number: int
    wal_file_name: str
    start_lsn: str
    end_lsn: str
    start_time: datetime
    end_time: datetime
    size_bytes: int
    has_gap: bool = False

class DBSnapshot(BaseModel):
    """Database snapshot manifest model."""
    snapshot_id: str
    instance_id: str
    snapshot_type: str = "manual"
    status: str = "COMPLETED"
    allocated_storage_gb: int
    redo_lsn: str
    timeline_id: int = 1
    snapshot_time: datetime

class EventOutboxEntry(BaseModel):
    """Outbox notification event model."""
    event_id: str
    event_identifier: str
    source_type: str
    source_identifier: str
    category: str
    message: str
    event_time: datetime
    status: str = "PENDING"
    retry_count: int = 0

class ControlPlaneReport(BaseModel):
    """Control plane state summary report."""
    status: str
    reason: Optional[str] = None
    total_instances: int
    available_instances: int
    active_replicas: int
    pending_events: int
    report_digest: str
