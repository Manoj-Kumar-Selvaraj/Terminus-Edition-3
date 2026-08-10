CREATE TABLE sonar_analysis (
  analysis_id TEXT PRIMARY KEY,
  project_key TEXT NOT NULL,
  status TEXT NOT NULL,
  scanner TEXT NOT NULL,
  gate_result TEXT NOT NULL,
  author TEXT NOT NULL,
  branch TEXT NOT NULL,
  token_kind TEXT NOT NULL,
  started_at TEXT NOT NULL,
  duration_sec INTEGER NOT NULL
);

CREATE TABLE postgres_identity (
  name TEXT PRIMARY KEY,
  address TEXT NOT NULL,
  port INTEGER NOT NULL,
  db_name TEXT NOT NULL,
  username TEXT NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE platform_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
