CREATE TABLE seed_records (
    record_id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    case_id TEXT,
    endpoint_id TEXT,
    platform TEXT NOT NULL,
    site_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    acquisition_mode TEXT NOT NULL,
    disposition TEXT NOT NULL,
    artifact_family TEXT NOT NULL
);
CREATE INDEX seed_records_case_idx ON seed_records(case_id, record_type);
CREATE INDEX seed_records_source_idx ON seed_records(source_id, platform, disposition);
