CREATE TABLE IF NOT EXISTS inventory_generations (
    generation_id bigserial PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants(tenant_id),
    state text NOT NULL CHECK(state IN ('collecting','complete','incomplete','abandoned')),
    required_shards integer NOT NULL CHECK(required_shards>0),
    successful_shards integer NOT NULL DEFAULT 0,
    unsupported_shards integer NOT NULL DEFAULT 0,
    failed_shards integer NOT NULL DEFAULT 0,
    record_count bigint NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL,
    finalized_at timestamptz,
    UNIQUE(tenant_id,generation_id)
);
CREATE INDEX IF NOT EXISTS inventory_generation_latest_idx ON inventory_generations(tenant_id,generation_id DESC,state);
CREATE TABLE IF NOT EXISTS inventory_shards (
    generation_id bigint NOT NULL REFERENCES inventory_generations(generation_id),
    shard_id text NOT NULL,
    disposition text NOT NULL CHECK(disposition IN ('pending','success','unsupported','failed')),
    cursor_token text,
    record_count integer NOT NULL DEFAULT 0,
    error_code text,
    error_detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY(generation_id,shard_id)
);
CREATE TABLE IF NOT EXISTS endpoint_inventory_staging (
    generation_id bigint NOT NULL REFERENCES inventory_generations(generation_id),
    tenant_id text NOT NULL,
    endpoint_id text NOT NULL,
    platform text NOT NULL,
    site_id text NOT NULL,
    state text NOT NULL,
    capabilities jsonb NOT NULL,
    last_seen_at timestamptz NOT NULL,
    PRIMARY KEY(generation_id,tenant_id,endpoint_id)
);
