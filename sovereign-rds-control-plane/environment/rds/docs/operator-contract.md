# Sovereign RDS Control Plane Operator Contract

The sovereign RDS control plane replaces AWS RDS management APIs for database instance provisioning, storage scaling, WAL-backed point-in-time recovery (PITR), parameter group dynamic vs static apply modes, read replica promotion, Multi-AZ failover fencing, and EventBridge outbox notifications.

## Primary System Architecture

The control plane is organized into four core entrypoints:

1. **REST API Server Daemon (`/app/rds/bin/rdsd`)**:
   - Listens on HTTP port 8080.
   - Handles declarative management calls for instances, snapshots, parameter groups, and event subscriptions.
   - Enforces multi-tenant account, region, and tenant_id isolation on all query projections.

2. **Async Worker Daemon (`/app/rds/bin/rds-worker`)**:
   - Background worker loop that checks WAL segment archive sequence continuity, calculates read replica streaming replication lag, manages Multi-AZ failover leader leases, and dispatches EventBridge outbox notifications.

3. **CLI Operator Tool (`/app/rds/bin/rdsctl`)**:
   - Command-line interface for human operators and verifier scripts to list instances, trigger failovers, perform snapshots, inspect outbox queues, and generate control plane state reports.

4. **Estate Fixture Generator (`/app/rds/bin/generate-estate`)**:
   - Populates PostgreSQL 16 control plane database with exactly 14,800 primary estate records across 100 DBInstances, 14,000 WAL archives, 400 DBSnapshots, and 300 outbox events.

## System Policy Requirements

### 1. DBInstance Lifecycle & Status Fencing

- **Status Precondition**: Instance modification requests (`ModifyDBInstance`), parameter group attachments, or backup retention changes are permitted only when instance status is `AVAILABLE`. Calling modify on instances in `CREATING`, `MODIFYING`, `REBOOTING`, `FAILOVER`, or `DELETING` status raises `InvalidInstanceStateError`.
- **Storage Allocation Growth**: Storage capacity changes (`allocated_storage_gb`) must be strictly monotonic. Size reductions or auto-scaling targets less than or equal to current allocated storage raise `StorageShrinkError`.
- **Deletion Protection**: Instances with `DeletionProtection = true` reject `DeleteDBInstance` API calls with `DeletionProtectionError`, regardless of whether `FinalDBSnapshotIdentifier` is specified.
- **Reboot & Process Reload**: Calling `RebootDBInstance` reloads database process configuration and applies pending static parameters.

### 2. WAL Ingestion & Point-In-Time Recovery (PITR)

- **WAL Archive Ingestion**: PostgreSQL WAL segment files (e.g. `000000010000000000000001`) are cataloged with timeline ID, sequence number, start LSN, and end LSN. Sequence gaps raise `WALContinuityError`.
- **Base Backup LSN Binding**: Snapshots record `redo_lsn` and `timeline_id`. PITR restores match base snapshots with WAL archives starting at or before the base backup LSN.
- **Target Restorable Window**: `RestoreDBInstanceToPointInTime` target timestamps must fall strictly within `[EarliestRestorableTime, LatestRestorableTime]`. Target timestamps outside this window raise `PITRWindowError`.

### 3. Parameter Group Dynamic vs Static Apply Modes

- **Dynamic Parameters**: Parameters declared as `apply_type = dynamic` apply immediately upon `ModifyDBParameterGroup`.
- **Static Parameters**: Parameters declared as `apply_type = static` set instance `PendingRebootParameters = true` without mutating runtime database process configuration until instance reboot.
- **Parameter Inheritance**: Modifying a parameter group merges custom parameter overrides into inherited parameter family defaults (`postgres16`).
- **Boot Validation**: Rebooting validates static parameter values against parameter catalog rules. `PendingRebootParameters` is cleared (`false`) only if boot validation passes.
- **Reset Parameter Group**: Calling `ResetDBParameterGroup` sets instance `parameter_group_status` to `pending-reboot`.

### 4. Read Replica Promotion & Replication Lag Fencing

- **Replication Lag Gate**: `PromoteReadReplica` verifies `replication_lag_bytes <= MaximumAllowedLagBytes` (10 MB). Promotion attempts with higher lag or `replication_status = UNKNOWN` raise `ReplicationLagError`.
- **LSN Flush Catch-Up**: The read replica must catch up its flush LSN (`flush_lsn >= primary_write_lsn`) before assuming the primary role.
- **Primary Write Lease Revocation**: Former primary instance write leases (`write_lease_owner`) are revoked before replica promotion to prevent split-brain dual-primary writes.
- **Endpoint Routing**: Primary writer and reader endpoints are updated atomically upon promotion.

### 5. Multi-AZ Automatic Failover Fencing

- **Leader Lease Fencing**: Failover workers must acquire an exclusive leader lease in `failover_leases` with TTL (15s).
- **Health Probe Isolation**: Direct TCP database port (5432) health probes are distinguished from control plane database connection pool latency to prevent false-positive failovers.
- **VIP Migration**: Floating VIP migration flushes route tables and issues gratuitous ARP announcements to update network switch ARP caches.

### 6. Event Outbox Notifications & Deduplication

- **Transactional Enqueue**: Outbox events enqueue transactionally inside the same database transaction as instance state changes.
- **Subscription Category Filters**: EventBridge subscriptions filter events strictly by `SourceType` (e.g. `db-instance`) and event category.
- **Deterministic Deduplication**: Event retries calculate deterministic `EventIdentifier` hashes from `source_type`, `source_identifier`, `event_time`, and `message` to prevent duplicate notification deliveries.
- **Audit Logging**: Failed deliveries record failure evidence in `event_delivery_audit` when retries exceed `max_event_retries` (5).

### 7. State Snapshots & Output Deliverables

Upon completion, the control plane generates:
- `/app/rds/out/rds-snapshot.json`: Canonical JSON snapshot with sorted keys and SHA-256 digest (`report_digest`).
- `/app/rds/out/instances.jsonl`: JSON lines list of visible DBInstances.
- `/app/rds/out/events.jsonl`: JSON lines list of outbox notification events.
- `/app/rds/out/health.json`: Health check, replication lag, and readiness summary.
