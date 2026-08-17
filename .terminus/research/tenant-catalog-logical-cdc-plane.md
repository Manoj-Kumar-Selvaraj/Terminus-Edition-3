# Scenario research — tenant-catalog-logical-cdc-plane

Creation profile: `large_system_strict`
Requested domain: Databases, with integration across several storage topics.

## Public technical grounding

Calibration only. Do not copy wording, topology, tests, or solution shape.

- PostgreSQL MVCC / snapshot isolation: xmin/xmax visibility, snapshot of committed xids
- PostgreSQL logical decoding / replication slots: decode committed WAL, LSN monotonic apply, slot epoch
- Constraint timing: UNIQUE/FK/CHECK evaluated against the writer's snapshot plus its write set
- Secondary indexes as derived structures that must match visible heap after commit and after redo
- Checkpoint + redo of committed records only

## Local / golden novelty

No Edition 3 task uses `subcategory = "Databases"`. Nearby work uses SQLite or PostgreSQL as an application store (`workshop-slot-transaction-control`, `webhook-outbox-delivery-plane`, `event-time-session-window-processor`, `jetstream-regional-stream-continuity`) rather than integrating snapshot visibility, constraints, indexes, logical CDC, and replica apply.

Golden references `wal-recovery-ordering` and `mvcc-lsm-compaction` are forbidden as scenario/topology copies. This work package is logical CDC + constraint/index coupling, not physical page redo and not LSM compaction.

## Candidates

### DB-A — snapshot catalog with WAL-decoded CDC and fenced replica apply (recommended)

Persona: catalog-platform engineer completing the OLTP/CDC cutover for a multi-tenant SKU desk.

Engineering objective: inherited Python catalog plane must commit under snapshot isolation, enforce PK/unique/FK/check against that snapshot, maintain secondary indexes in the same commit, decode CDC only from committed WAL, apply to the replica with LSN and epoch fencing in FK-safe order, and redo from checkpoint without installing uncommitted work.

Required end state: heap, indexes, WAL, replica, and operator reports agree after commit, crash recover, decode, and apply.

Requirement families: visibility, commit protocol, constraints, indexes, logical decode, replica apply, checkpoint redo, CLI fail-closed, frozen-tenant safety.

Inherited state: ~12k versioned catalog rows, a WAL with committed history plus a crashed uncommitted txn, a replica slot behind the durable LSN, oncall notes and a bounce log.

Partial-fix traps: dual-write CDC from heap; sort replica by pk instead of LSN; rebuild indexes from all versions; recover by replaying every WAL kind; bump epoch on inspect.

Scale fit: strong. Natural 12k versions, 7–8 root-cause clusters, 20–30 manifestations, 25–30 distinct F2P behaviors.

Duplicate risk: low if physical WAL page recovery and LSM compaction are not used as the plot.

### DB-B — online unique-index rebuild during snapshot writes

Persona: DBA running CREATE INDEX CONCURRENTLY analogue.

Scale fit: medium. Interesting visibility vs index build, but CDC/replica/recovery fall out unless piled on. Disposition: rejected as too narrow; unique-index visibility becomes a cluster inside DB-A.

### DB-C — two-phase commit across catalog shard and payment shard

Persona: payments/catalog integration owner.

Scale fit: medium-high but the second shard is a different product surface and risks becoming two tasks glued together. Disposition: rejected; keep one catalog plane.

### DB-D — PostgreSQL logical-replication slot rewind after sequence reset

Persona: replica operator after publisher rebuild.

Scale fit: medium. Real ops problem, but using live PostgreSQL overlaps `workshop-slot-transaction-control` (app transactions on Postgres) and is easy to reduce to config knobs. Disposition: rejected; encode slot/epoch fencing inside the inherited catalog plane instead.

## Recommendation

Use DB-A. It is one coherent Databases work package whose difficulty is the interaction of snapshot visibility, constraints, indexes, WAL-sourced CDC, and fenced apply/recovery — the integration the request asked for — without copying golden WAL/LSM topologies.
