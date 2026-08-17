# DEFECT_TOPOLOGY — tenant-catalog-logical-cdc-plane

STATUS: TOPOLOGY_READY

Against the approved Go architecture. Inject only these clusters into starter packages. Oracle repairs the same packages.

Root causes and manifestations remain those in `tenant-catalog-logical-cdc-plane.json` (RC_VIS, RC_CDC, RC_CON, RC_IDX, RC_APPLY, RC_RECOVER, RC_CLI; D01–D25).

Starter injection targets (Go):

- `internal/snapshot` — latest xmax-null, leak uncommitted
- `internal/cdc` — heap scan, heap row numbers as lsn
- `internal/constraints` — replica lag unique, skip frozen/FK/hold aggregate
- `internal/indexes` — index all versions, prepare before COMMIT
- `internal/replica` — reverse FK order, ignore LSN/epoch fence
- `internal/recover` — redo uncommitted, bump epoch
- `internal/inspect` — recover as side effect
- `internal/cli` — WAL append before argv parse; --reset-output truncates WAL

Do not inject defects into `internal/store`, `internal/wal` append primitives, `internal/schema`, `cmd/seed`, or warehouse files.
