# Catalog plane contract

The desk under `/app/catalog` is a snapshot-isolated OLTP catalog. Heap versions, secondary indexes, the logical WAL, and the replica are different layers. CDC is a decode of committed WAL, not a heap dump. Replica apply is a consumer of that decode.

Operator entrypoint: `/app/catalog/bin/catalogctl`. Binding knobs: `/app/catalog/config/catalog.json`. Leave `/app/catalog/warehouse` untouched.

## Paths

| Role | Path |
| --- | --- |
| Heap versions | `/app/catalog/data/engine.sqlite` table `row_version` |
| Logical WAL | `/app/catalog/data/wal.jsonl` |
| Checkpoint | `/app/catalog/data/checkpoint.json` |
| Secondary indexes | `/app/catalog/data/indexes.json` |
| Replica | `/app/catalog/data/replica.sqlite` |
| Replica slot | `/app/catalog/data/replica_slot.json` |
| CDC output | `/app/catalog/out/cdc.jsonl` |
| Health | `/app/catalog/out/health.json` |
| Apply report | `/app/catalog/out/apply-report.json` |
| Rejects | `/app/catalog/out/rejects.jsonl` |
| Warehouse dump | `/app/catalog/warehouse/inventory.sqlite` |

## Tables

Logical tables, FK rank for apply (parents first): `tenant` 0, `sku` 1, `offer` 2, `hold` 3.

- `tenant`: pk `tenant_id`. `status` is `ACTIVE` or `FROZEN`.
- `sku`: pk `sku_id`. Required `tenant_id`. Unique among visible rows: `(tenant_id, sku_code)`.
- `offer`: pk `offer_id`. Required `sku_id` and `tenant_id`. Unique among visible rows: `(tenant_id, offer_code)`. `qty_on_hand` is an integer `>= 0`.
- `hold`: pk `hold_id`. Required `offer_id` and `tenant_id`. `qty` is an integer `> 0`. For a visible offer, the sum of visible hold `qty` must be `<=` that offer's `qty_on_hand`.

A `FROZEN` tenant rejects INSERT or UPDATE of `offer` or `hold`. Tenant and sku maintenance on a frozen tenant is still allowed.

## Identifiers and WAL

`txn_id` and `lsn` are positive integers. `lsn` is assigned strictly increasing on each WAL append. A transaction is:

`BEGIN` then zero or more of `INSERT` / `UPDATE` / `DELETE` then exactly one of `COMMIT` or `ABORT`.

WAL record objects use keys `lsn`, `txn_id`, `kind`, `epoch`, and for mutations also `table`, `pk`, `before`, `after`. `before` is null on INSERT. `after` is null on DELETE. UPDATE carries both.

Commit durability: a transaction is committed only when its `COMMIT` record is in `/app/catalog/data/wal.jsonl`. Heap and index installation happen after that append, never before.

## Snapshot isolation

A snapshot is the `txn_id` assigned at BEGIN.

A heap version is visible to snapshot `S` when all of these hold:

1. `xmin` is committed, or `xmin == S` (read-your-writes).
2. `xmin <= S`.
3. `xmax` is null, or `xmax` is not committed, or `xmax > S`. A committed delete/update sets `xmax` to the writer's `txn_id`.

Uncommitted work from any other transaction is invisible. After a committed UPDATE, the pre-image (`xmax = writer`) is not visible to later snapshots; the post-image (`xmin = writer`) is. After a committed DELETE, no version of that pk is visible.

## Constraints

Evaluate at COMMIT against the writer's snapshot plus its own write set. Do not use replica lag, warehouse rows, or uncommitted versions from other transactions.

Fail closed with a reject object `{txn_id, code, table, pk, detail}` appended to rejects.jsonl and ABORT the transaction (WAL `ABORT`, no heap/index install). Codes:

- `PK_CONFLICT`
- `UNIQUE_CONFLICT`
- `FK_MISSING`
- `CHECK_FAIL`
- `FROZEN_TENANT`
- `HOLD_QTY`

Unknown tables, missing pk, or non-integer qty fields are `CHECK_FAIL`.

## Secondary indexes

`indexes.json` is an object with keys `sku_code` and `offer_code`. Each maps a string `"tenant_id\\0code"` to the visible pk. Rebuild from currently visible committed heap rows after every successful COMMIT and after recover. Aborted and invisible versions must not remain in the index.

## Logical CDC

`catalogctl decode` walks WAL from `replica_slot.confirmed_lsn + 1` through the durable max lsn. Emit one CDC object per committed mutation, in WAL lsn order:

```
lsn, txn_id, epoch, table, op, pk, before, after
```

`op` is `insert`, `update`, or `delete` matching the WAL kind. Skip txns that have no `COMMIT`. Do not scan the heap to invent records. Write `/app/catalog/out/cdc.jsonl` (replace the file). Decode does not apply to the replica and does not advance the slot.

## Replica apply

`catalogctl apply` reads CDC JSONL (default `/app/catalog/out/cdc.jsonl`). For each record:

- If `epoch` != `replica_slot.epoch`, reject the whole batch: apply nothing, do not advance `confirmed_lsn`, `rejected` equals the batch length.
- If `lsn <= replica_slot.confirmed_lsn`, skip it (`skipped`).
- Otherwise apply in lsn order. Records that share a `txn_id` are applied in FK rank (tenant, sku, offer, hold) and, within a rank, by lsn.

INSERT/UPDATE upsert the replica table row keyed by pk. DELETE removes it. Replica schema is `/app/catalog/sql/replica_schema.sql`.

On a clean batch, `replica_slot.confirmed_lsn` becomes the max applied lsn. Write `/app/catalog/out/apply-report.json`:

```
applied, skipped, rejected, confirmed_lsn, epoch
```

All five fields are integers (`epoch` included).

## Checkpoint and recover

`catalogctl checkpoint` writes `/app/catalog/data/checkpoint.json` with `lsn` equal to the durable WAL max, plus `txn_id`, `epoch`, and a copy of visible committed heap identity (not uncommitted). It does not change replica epoch.

`catalogctl recover` restores heap and indexes from that checkpoint, then redos WAL records with `lsn > checkpoint.lsn` that belong to committed transactions. Uncommitted WAL is not installed. Recover does not bump `replica_slot.epoch`. After redo, rebuild indexes from visible committed rows.

## CLI

Commands: `commit`, `decode`, `apply`, `recover`, `checkpoint`, `inspect`, `empty-check`.

- Unknown flags or an unknown command exit 2 before any WAL, heap, index, replica, or slot mutation.
- `commit` requires `--input <path>` to a JSONL of mutation objects `{op, table, pk, payload}`. `op` is `insert`, `update`, or `delete`. Missing `--input` exits 2 without opening a transaction.
- `apply` may take `--cdc <path>` to read CDC JSONL from a file other than `/app/catalog/out/cdc.jsonl`. When `--cdc` is omitted, apply reads the default CDC path. Unknown flags still exit 2.
- `--reset-output` may delete files under `/app/catalog/out/` only. It must not truncate WAL, heap, indexes, checkpoint, replica, slot, or warehouse.
- `inspect` and `empty-check` rewrite health.json from observed state and must not append WAL, change heap, rebuild indexes, apply CDC, or change the replica slot.
- `empty-check` still requires the engine database and writes health.json. It does not assign a txn_id.

Exit 0 on success. Business rejects from constraints are exit 0 with rejects.jsonl populated and no commit. Usage errors are exit 2.

## Health report

Every successful `commit`, `recover`, `decode`, `apply`, `checkpoint`, `inspect`, and `empty-check` rewrites `/app/catalog/out/health.json`:

- `generated_at`: RFC 3339 text with an explicit UTC offset, or a finite Unix timestamp in seconds
- `epoch`: integer, current replica slot epoch
- `durable_lsn`: integer max WAL lsn, or 0 if WAL is empty
- `checkpoint_lsn`: integer from checkpoint.json, or 0 if missing
- `replica_confirmed_lsn`: integer
- `replica_epoch`: integer, same as `epoch`
- `heap_visible_count`: integer count of committed-visible rows at a snapshot equal to the latest committed txn_id
- `cdc_source`: the string `wal`
- `index_ok`: true iff both secondary indexes match visible committed heap rows
- `visibility_ok`: true iff no uncommitted version is visible at that snapshot
- `constraints_ok`: true iff currently visible committed rows satisfy PK/unique/FK/check/frozen/hold-qty
- `replica_ok`: true iff every replica row with a pk has a visible committed heap row of the same table/pk, and `replica_confirmed_lsn <= durable_lsn`
- `recovery_ok`: true iff every WAL record with lsn > checkpoint_lsn that lacks a txn COMMIT is absent from the heap
- `healthy`: conjunction of `index_ok`, `visibility_ok`, `constraints_ok`, `replica_ok`, `recovery_ok`

Warehouse files are a production dump. Do not use them as the commit snapshot, CDC source, or replica apply source.
