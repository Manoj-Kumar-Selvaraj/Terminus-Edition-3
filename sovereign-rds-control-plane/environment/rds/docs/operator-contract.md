# Sovereign RDS Control Plane Operator Contract

This document describes the local control-plane surfaces operators use in place of AWS RDS management APIs. Detailed PITR, parameter-group, and failover fencing rules live in the sibling contracts under `/app/rds/docs/`.

## Entrypoints

1. **`/app/rds/bin/rdsd`** — HTTP API on port 8080 for instances, snapshots, parameter groups, and event subscriptions. Describe/list projections are scoped by account, region, and `tenant_id`.
2. **`/app/rds/bin/rds-worker`** — Background loop for WAL continuity checks, replica lag, Multi-AZ failover leases, and EventBridge outbox delivery.
3. **`/app/rds/bin/rdsctl`** — Operator CLI for list/failover/snapshot/outbox inspection and report generation.
4. **`/app/rds/bin/generate-estate`** — Seeds the PostgreSQL 16 control DB with the fixed lab estate (100 instances, 14,000 WAL archives, 400 snapshots, 300 outbox events → 14,800 primary records).

## Cross-cutting invariants

- Instance mutations that change lifecycle state require status `AVAILABLE` unless a sibling contract defines a narrower path (reboot, failover, restore).
- Storage growth on `allocated_storage_gb` is strictly upward; equal or smaller targets raise `StorageShrinkError`.
- `DeletionProtection = true` blocks `DeleteDBInstance` (`DeletionProtectionError`) even when `FinalDBSnapshotIdentifier` is set.
- Outbox enqueue shares the same database transaction as the instance state change that produced the event.
- EventBridge subscription matching uses `SourceType` plus event category. `SourceIdentifier` appears in payloads and `EventIdentifier` material; it is not the subscription match key.
- Deterministic `EventIdentifier` hashes combine `source_type`, `source_identifier`, `event_time`, and `message`. After `max_event_retries = 5`, write `event_delivery_audit`.
- Instance state transitions write durable transaction checkpoints; restart skips already-committed checkpointed work.
- Readiness is `READY` only when visible instances are `AVAILABLE` and outbox/backlog queues are empty; otherwise `UNHEALTHY`.
- Replica promotion revokes the former primary write lease and sets that instance to `READ_ONLY` before endpoint swap. Promotion must not set `route_table_flushed` or `gratuitous_arp_sent`.

## Report artifacts

Operators (and verifier tooling) expect:

| Path | Notes |
|------|--------|
| `/app/rds/out/rds-snapshot.json` | Canonical sorted keys; SHA-256 `report_digest` over the stable field subset below |
| `/app/rds/out/instances.jsonl` | Required UTF-8 JSON lines companion (no digest; ordering not separately graded) |
| `/app/rds/out/events.jsonl` | Required UTF-8 JSON lines companion (no digest; ordering not separately graded) |
| `/app/rds/out/health.json` | Required UTF-8 health / lag / readiness companion (no digest field; key order not separately graded) |

Only `rds-snapshot.json` is graded for canonical key ordering and `report_digest`. Companion files must exist as UTF-8 JSON/JSONL without per-file digests.

### `report_digest` stable subset

Digest input is the canonical JSON encoding (sorted keys) of:

- top-level: `status`, `total_instances`, `available_instances`, `active_replicas`, `pending_events`
- `instances`: array sorted by `instance_id`, each element limited to `instance_id`, `status`, `db_instance_class`, `allocated_storage_gb`, `pending_reboot_parameters`, `multi_az`

Volatile extras outside this subset must not change `report_digest`.
