ALTER TABLE cases ADD COLUMN IF NOT EXISTS created_by text;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS closed_at timestamptz;
CREATE TABLE IF NOT EXISTS collection_attempts (
    item_id text NOT NULL REFERENCES collection_items(item_id),
    attempt integer NOT NULL,
    worker_id text NOT NULL,
    attempt_token text NOT NULL,
    state text NOT NULL,
    dispatched_at timestamptz,
    acknowledged_at timestamptz,
    completed_at timestamptz,
    result_digest text,
    result_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY(item_id, attempt),
    UNIQUE(attempt_token)
);
CREATE INDEX IF NOT EXISTS attempts_state_idx ON collection_attempts(state, updated_at);
CREATE TABLE IF NOT EXISTS source_dispositions (
    item_id text PRIMARY KEY REFERENCES collection_items(item_id),
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    endpoint_id text NOT NULL,
    source_id text NOT NULL,
    disposition text NOT NULL,
    accepted_bytes bigint NOT NULL DEFAULT 0,
    expected_bytes bigint,
    terminal_reason text,
    last_observation_at timestamptz,
    revision bigint NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS source_dispositions_case_idx ON source_dispositions(tenant_id, case_id, disposition, item_id);
CREATE TABLE IF NOT EXISTS endpoint_aliases (
    tenant_id text NOT NULL,
    endpoint_id text NOT NULL,
    alias text NOT NULL,
    alias_kind text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_until timestamptz,
    PRIMARY KEY(tenant_id, alias, alias_kind, valid_from)
);
CREATE TABLE IF NOT EXISTS plan_revisions (
    plan_id text NOT NULL REFERENCES collection_plans(plan_id),
    revision integer NOT NULL,
    digest text NOT NULL,
    document jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY(plan_id, revision)
);
CREATE TABLE IF NOT EXISTS export_artifacts (
    export_id text NOT NULL REFERENCES export_jobs(export_id),
    evidence_id text NOT NULL REFERENCES evidence_items(evidence_id),
    digest text NOT NULL,
    byte_length bigint NOT NULL,
    ordinal integer NOT NULL,
    PRIMARY KEY(export_id, evidence_id),
    UNIQUE(export_id, ordinal)
);
CREATE TABLE IF NOT EXISTS retention_references (
    reference_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    evidence_id text NOT NULL REFERENCES evidence_items(evidence_id),
    reference_type text NOT NULL,
    owner_id text NOT NULL,
    retain_until timestamptz,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS retention_evidence_idx ON retention_references(evidence_id, retain_until);
CREATE TABLE IF NOT EXISTS seed_records (
    record_id text PRIMARY KEY,
    record_type text NOT NULL,
    tenant_id text NOT NULL,
    case_id text,
    payload jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS seed_records_type_idx ON seed_records(record_type, record_id);
CREATE TABLE IF NOT EXISTS event_observations (
    observation_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    item_id text NOT NULL REFERENCES collection_items(item_id),
    attempt integer NOT NULL,
    source_id text NOT NULL,
    source_time timestamptz,
    normalized_time timestamptz,
    time_uncertainty_ms bigint NOT NULL DEFAULT 0,
    trait text NOT NULL,
    event_payload jsonb NOT NULL,
    payload_digest text NOT NULL,
    accepted boolean NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS observations_case_time_idx ON event_observations(tenant_id, case_id, normalized_time, observation_id);
