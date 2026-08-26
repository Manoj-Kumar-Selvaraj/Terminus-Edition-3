CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS db_instances (
    instance_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(12) NOT NULL,
    region VARCHAR(50) NOT NULL,
    engine VARCHAR(50) NOT NULL DEFAULT 'postgres',
    engine_version VARCHAR(20) NOT NULL DEFAULT '16.2',
    db_instance_class VARCHAR(50) NOT NULL DEFAULT 'db.m6i.xlarge',
    allocated_storage_gb INTEGER NOT NULL DEFAULT 100,
    storage_type VARCHAR(20) NOT NULL DEFAULT 'gp3',
    status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    deletion_protection BOOLEAN NOT NULL DEFAULT TRUE,
    multi_az BOOLEAN NOT NULL DEFAULT FALSE,
    publicly_accessible BOOLEAN NOT NULL DEFAULT FALSE,
    master_username VARCHAR(64) NOT NULL DEFAULT 'postgres',
    endpoint_address TEXT,
    endpoint_port INTEGER NOT NULL DEFAULT 5432,
    parameter_group_name VARCHAR(64) NOT NULL DEFAULT 'default.postgres16',
    pending_reboot_parameters BOOLEAN NOT NULL DEFAULT FALSE,
    parameter_group_status VARCHAR(50) NOT NULL DEFAULT 'in-sync',
    backup_retention_period INTEGER NOT NULL DEFAULT 7,
    earliest_restorable_time TIMESTAMPTZ,
    latest_restorable_time TIMESTAMPTZ,
    primary_instance_id VARCHAR(64),
    replication_status VARCHAR(50),
    replication_lag_bytes BIGINT DEFAULT 0,
    write_lease_owner VARCHAR(64),
    write_lease_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS db_parameter_groups (
    parameter_group_name VARCHAR(64) PRIMARY KEY,
    family VARCHAR(50) NOT NULL DEFAULT 'postgres16',
    description TEXT,
    parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parameter_definitions (
    parameter_name VARCHAR(128) PRIMARY KEY,
    family VARCHAR(50) NOT NULL DEFAULT 'postgres16',
    apply_type VARCHAR(20) NOT NULL DEFAULT 'dynamic',
    data_type VARCHAR(20) NOT NULL DEFAULT 'string',
    allowed_values TEXT,
    default_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wal_archives (
    id BIGSERIAL PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL REFERENCES db_instances(instance_id),
    timeline_id INTEGER NOT NULL DEFAULT 1,
    sequence_number BIGINT NOT NULL,
    wal_file_name VARCHAR(128) NOT NULL,
    start_lsn VARCHAR(64) NOT NULL,
    end_lsn VARCHAR(64) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    size_bytes BIGINT NOT NULL,
    has_gap BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (instance_id, timeline_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS db_snapshots (
    snapshot_id VARCHAR(128) PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL REFERENCES db_instances(instance_id),
    snapshot_type VARCHAR(20) NOT NULL DEFAULT 'manual',
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    allocated_storage_gb INTEGER NOT NULL,
    redo_lsn VARCHAR(64) NOT NULL,
    timeline_id INTEGER NOT NULL DEFAULT 1,
    snapshot_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS failover_leases (
    instance_id VARCHAR(64) PRIMARY KEY REFERENCES db_instances(instance_id),
    leader_worker_id VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    vip_address VARCHAR(45) NOT NULL
);

CREATE TABLE IF NOT EXISTS event_outbox (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL UNIQUE,
    event_identifier VARCHAR(128) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_identifier VARCHAR(64) NOT NULL,
    category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_subscriptions (
    subscription_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(12) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    target_endpoint TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_delivery_audit (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL,
    subscription_id VARCHAR(64) NOT NULL,
    delivery_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id VARCHAR(64) PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,
    instance_id VARCHAR(64) NOT NULL,
    state_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instances_tenant_region ON db_instances(tenant_id, account_id, region);
CREATE INDEX IF NOT EXISTS idx_wal_instance_time ON wal_archives(instance_id, timeline_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_snapshots_instance ON db_snapshots(instance_id, snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON event_outbox(status, created_at) WHERE status = 'PENDING';
