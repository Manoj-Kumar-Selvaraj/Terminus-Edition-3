-- Inherited authz decision warehouse used by platform reporting (not the live evaluator).
CREATE TABLE authz_events (
  event_id INTEGER PRIMARY KEY,
  principal TEXT NOT NULL,
  action TEXT NOT NULL,
  repo TEXT NOT NULL,
  reference TEXT NOT NULL,
  allowed INTEGER NOT NULL,
  source_ip TEXT NOT NULL,
  mfa INTEGER NOT NULL,
  decided_at TEXT NOT NULL
);

CREATE INDEX idx_authz_principal ON authz_events(principal);
CREATE INDEX idx_authz_action ON authz_events(action);
CREATE INDEX idx_authz_repo ON authz_events(repo);
CREATE INDEX idx_authz_day ON authz_events(decided_at);
