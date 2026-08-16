# Operator notes

Binaries live under `/app/outbox/bin`. Prefer `OUTBOX_SYNC=1` for deterministic claim/deliver tests.

Seeded catalog includes tenants `acme`, `globex`, `initech`, `umbrella`, `stark`, and `wayne` with three endpoints each. Historical outbox rows are preloaded for capacity smoke checks; verification suites typically use a fresh temp database.

HMAC secrets in local seed data are fixture values, not production credentials.
