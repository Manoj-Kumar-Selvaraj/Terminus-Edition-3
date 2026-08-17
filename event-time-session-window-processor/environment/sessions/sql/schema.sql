-- Operator catalog for the click warehouse. The JSONL dump remains the
-- inherited production ledger; this SQLite file is the indexed inventory
-- the processor desk reads for tenant/user/kind coverage.

CREATE TABLE tenant (
    tenant_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    plan TEXT NOT NULL,
    created_event_time_ms INTEGER NOT NULL
);

CREATE TABLE click_user (
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    cohort TEXT NOT NULL,
    first_seen_ms INTEGER NOT NULL,
    PRIMARY KEY (tenant_id, user_id),
    FOREIGN KEY (tenant_id) REFERENCES tenant (tenant_id)
);

CREATE TABLE ingest_batch (
    batch_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    source TEXT NOT NULL,
    recorded_at_ms INTEGER NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenant (tenant_id)
);

CREATE TABLE click_event (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_time_ms INTEGER NOT NULL,
    payload TEXT NOT NULL,
    channel TEXT NOT NULL,
    kind TEXT NOT NULL,
    page TEXT NOT NULL,
    device TEXT NOT NULL,
    country TEXT NOT NULL,
    ingest_batch_id INTEGER NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenant (tenant_id),
    FOREIGN KEY (ingest_batch_id) REFERENCES ingest_batch (batch_id)
);

CREATE INDEX idx_click_event_tenant_user_time
    ON click_event (tenant_id, user_id, event_time_ms);

CREATE INDEX idx_click_event_kind ON click_event (kind);
CREATE INDEX idx_click_event_channel ON click_event (channel);
CREATE INDEX idx_click_event_batch ON click_event (ingest_batch_id);

CREATE TABLE processor_run (
    run_id INTEGER PRIMARY KEY,
    started_event_time_ms INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    feed_mode INTEGER NOT NULL,
    observed_count INTEGER NOT NULL,
    closed_count INTEGER NOT NULL,
    too_late_count INTEGER NOT NULL
);
