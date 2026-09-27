CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id text PRIMARY KEY,
    display_name text NOT NULL,
    active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS actors (
    actor_id text PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    role text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    UNIQUE(actor_id, tenant_id)
);
CREATE TABLE IF NOT EXISTS cases (
    case_id text PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    title text NOT NULL,
    state text NOT NULL CHECK(state IN ('open','hold','closed')),
    revision bigint NOT NULL DEFAULT 1,
    opened_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE(case_id, tenant_id)
);
CREATE TABLE IF NOT EXISTS case_memberships (
    case_id text NOT NULL REFERENCES cases(case_id),
    actor_id text NOT NULL,
    permission text NOT NULL,
    granted_at timestamptz NOT NULL,
    PRIMARY KEY(case_id, actor_id, permission)
);
CREATE TABLE IF NOT EXISTS endpoints (
    endpoint_id text NOT NULL,
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    platform text NOT NULL,
    site_id text NOT NULL,
    state text NOT NULL CHECK(state IN ('active','quarantined','retired')),
    inventory_generation bigint NOT NULL,
    capabilities jsonb NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY(tenant_id, endpoint_id)
);
CREATE TABLE IF NOT EXISTS policy_revisions (
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    policy_revision text NOT NULL,
    document jsonb NOT NULL,
    digest text NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY(tenant_id, policy_revision)
);
CREATE TABLE IF NOT EXISTS collection_plans (
    plan_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    case_revision bigint NOT NULL,
    policy_revision text NOT NULL,
    inventory_generation bigint NOT NULL,
    requested_by text NOT NULL,
    intent jsonb NOT NULL,
    plan_digest text NOT NULL,
    state text NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE(plan_id, case_id),
    FOREIGN KEY(case_id, tenant_id) REFERENCES cases(case_id, tenant_id)
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    tenant_id text NOT NULL,
    actor_id text NOT NULL,
    idempotency_key text NOT NULL,
    plan_digest text NOT NULL,
    plan_id text NOT NULL REFERENCES collection_plans(plan_id),
    created_at timestamptz NOT NULL,
    PRIMARY KEY(tenant_id, actor_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS collection_items (
    item_id text PRIMARY KEY,
    plan_id text NOT NULL REFERENCES collection_plans(plan_id),
    case_id text NOT NULL,
    endpoint_id text NOT NULL,
    source_id text NOT NULL,
    mode text NOT NULL CHECK(mode IN ('live','offline')),
    artifact_families jsonb NOT NULL,
    byte_limit bigint NOT NULL,
    deadline timestamptz NOT NULL,
    required boolean NOT NULL,
    disposition text NOT NULL,
    active_attempt integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS worker_leases (
    lease_id text PRIMARY KEY,
    item_id text NOT NULL REFERENCES collection_items(item_id),
    attempt integer NOT NULL,
    worker_id text NOT NULL,
    token text NOT NULL,
    deadline timestamptz NOT NULL,
    acquired_at timestamptz NOT NULL,
    released_at timestamptz,
    UNIQUE(item_id, attempt)
);
CREATE TABLE IF NOT EXISTS dispatch_queue (
    queue_id bigserial PRIMARY KEY,
    item_id text NOT NULL REFERENCES collection_items(item_id),
    attempt integer NOT NULL,
    state text NOT NULL,
    available_at timestamptz NOT NULL,
    worker_id text,
    claim_token text,
    claim_deadline timestamptz,
    delivery_attempts integer NOT NULL DEFAULT 0,
    acknowledgement jsonb,
    last_error jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE(item_id, attempt)
);
CREATE INDEX IF NOT EXISTS dispatch_queue_ready_idx ON dispatch_queue(state, available_at, queue_id);
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id text PRIMARY KEY,
    payload_digest text NOT NULL,
    event_type text NOT NULL,
    received_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS event_inbox (
    event_id bigserial PRIMARY KEY,
    delivery_id text NOT NULL UNIQUE REFERENCES webhook_deliveries(delivery_id),
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    item_id text NOT NULL,
    attempt integer NOT NULL,
    source_id text NOT NULL,
    event_type text NOT NULL,
    occurred_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    state text NOT NULL DEFAULT 'received',
    claim_token text,
    claim_deadline timestamptz,
    consumed_at timestamptz
);
CREATE INDEX IF NOT EXISTS inbox_pending_idx ON event_inbox(state, event_id);
CREATE TABLE IF NOT EXISTS evidence_objects (
    digest text PRIMARY KEY,
    byte_length bigint NOT NULL,
    object_path text NOT NULL,
    complete boolean NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    endpoint_id text NOT NULL,
    source_id text NOT NULL,
    plan_id text NOT NULL,
    item_id text NOT NULL,
    attempt integer NOT NULL,
    digest text NOT NULL REFERENCES evidence_objects(digest),
    capture_time timestamptz NOT NULL,
    traits jsonb NOT NULL,
    validation_state text NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE(case_id, item_id, attempt, source_id, digest)
);
CREATE INDEX IF NOT EXISTS evidence_case_idx ON evidence_items(tenant_id, case_id, capture_time, evidence_id);
CREATE TABLE IF NOT EXISTS custody_events (
    custody_sequence bigserial PRIMARY KEY,
    custody_id text NOT NULL UNIQUE,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    evidence_id text NOT NULL REFERENCES evidence_items(evidence_id),
    actor_id text NOT NULL,
    action text NOT NULL,
    reason text NOT NULL,
    event_digest text NOT NULL,
    occurred_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS custody_case_idx ON custody_events(tenant_id, case_id, custody_sequence);
CREATE TABLE IF NOT EXISTS case_holds (
    hold_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    reason text NOT NULL,
    state text NOT NULL CHECK(state IN ('active','released')),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    released_by text,
    released_at timestamptz
);
CREATE TABLE IF NOT EXISTS audit_events (
    audit_sequence bigserial PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text,
    actor_id text NOT NULL,
    action text NOT NULL,
    decision text NOT NULL,
    detail jsonb NOT NULL,
    detail_digest text NOT NULL,
    occurred_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_case_idx ON audit_events(tenant_id, case_id, audit_sequence);
CREATE TABLE IF NOT EXISTS export_jobs (
    export_id text PRIMARY KEY,
    tenant_id text NOT NULL,
    case_id text NOT NULL,
    requested_by text NOT NULL,
    state text NOT NULL,
    manifest_digest text,
    object_path text,
    item_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL,
    published_at timestamptz
);
CREATE TABLE IF NOT EXISTS worker_checkpoints (
    worker_name text NOT NULL,
    stream text NOT NULL,
    position bigint NOT NULL,
    fence_token text NOT NULL,
    heartbeat_at timestamptz NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY(worker_name, stream)
);
