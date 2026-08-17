# SYSTEM_ARCHITECTURE — tenant-catalog-logical-cdc-plane

STATUS: ARCHITECTURE_READY

Creation profile: `large_system_strict`
Implementation language: Go (solver-visible runtime). Python is verifier-only.

This is the clean inherited system. No defects are injected here.

## COMPONENT_GRAPH

- `cmd/catalogctl` — operator CLI (commit, decode, apply, recover, checkpoint, inspect, empty-check)
- `cmd/seed` — deterministic catalog/WAL/replica/warehouse materializer used at image build
- `internal/engine` — facade wiring snapshot, txn, constraints, indexes, CDC, replica, recover, inspect
- `internal/store` — engine sqlite heap + replica sqlite + WAL jsonl + checkpoint/indexes/slot files
- `internal/wal` — append-only logical WAL, committed-txn detection
- `internal/snapshot` — xmin/xmax snapshot isolation
- `internal/txn` — BEGIN/mutate/COMMIT/ABORT; heap install only after WAL COMMIT
- `internal/constraints` — PK/unique/FK/check/frozen/hold-qty against writer snapshot ∪ write set
- `internal/indexes` — sku_code / offer_code maps from committed-visible heap
- `internal/cdc` — decode committed WAL mutations
- `internal/replica` — LSN/epoch-fenced apply in FK order
- `internal/recover` — checkpoint restore + redo of committed WAL only
- `internal/inspect` — health.json from observed state, no mutation
- `internal/schema`, `internal/model`, `internal/paths`, `internal/policy`, `internal/health`

## ENTRYPOINTS

- `/app/catalog/bin/catalogctl` (built from `cmd/catalogctl`)
- `/app/catalog/bin/seed` (image-build / operator seed)
- Env: `CATALOG_ROOT` (default `/app/catalog`)
- Config: `/app/catalog/config/catalog.json`
- Contract: `/app/catalog/docs/catalog-contract.md`

## STATE_MODEL

Source of truth for commits is the logical WAL. Heap versions (`row_version`) and secondary indexes are derived after COMMIT. Replica sqlite is a consumer of decoded CDC, fenced by `replica_slot.json` (epoch, confirmed_lsn). Checkpoint captures committed heap + durable lsn. Warehouse sqlite is an immutable production dump.

## SOLVER_VISIBLE_DOC_PLAN

- `docs/catalog-contract.md` — visibility, WAL, constraints, CDC, apply, recover, CLI, report schemas
- `sql/schema.sql`, `sql/replica_schema.sql` — physical layouts
- `notes/oncall.md` + `logs/bounce.log` — inherited incident evidence, not a repair map

## PRODUCTION_CHARACTERISTICS

Differentiated Go packages, real CLI, sqlite persistence, restart/recover, fail-closed rejects, idempotent apply, 12k versioned rows with replica lag.

## SCALE_FIT

Natural 12k `row_version` rows, 7 root-cause clusters after A3, 25–30 organic F2P from CLI/visibility/constraints/CDC/apply/recover/index/health surfaces. Go runtime LOC expected well above 3,000 without counting seed.sql.

## RESOURCE_GRAPH

engine.sqlite, wal.jsonl, checkpoint.json, indexes.json, replica.sqlite, replica_slot.json, warehouse/inventory.sqlite, out/{health,apply-report,cdc,rejects}

## DATA_VOLUME_PLAN

40 tenants, 800 skus, 6400 live offers, 3200 holds, 1560 historical offer versions → 12000 `row_version` rows. Replica confirmed through tenant+sku WAL only.

## UNRESOLVED_RISKS

modernc.org/sqlite must be baked at image build (`go mod tidy` + `go build`). No Python in the agent runtime path.
