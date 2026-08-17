# tenant-catalog-logical-cdc-plane

Snapshot isolation, commit-time constraints, secondary indexes, logical CDC, and replica apply have to agree on the same WAL. A heap dump that looks complete can still leak an uncommitted crash insert into CDC, rewind a replica slot, or leave indexes pointing at aborted versions.

Keep the Go catalog plane and WAL protocol. Visibility uses xmin/xmax. Constraints see the writer snapshot plus its write set. Indexes rebuild from committed-visible rows after COMMIT and after recover. decode walks committed WAL; apply is monotonic in LSN, fenced by epoch, and FK-ordered inside a txn. Checkpoint redo skips uncommitted records. inspect does not recover. Warehouse stays put.

The verifier drives `catalogctl` against isolated copies of the transferred `/app/catalog` tree: usage errors leave WAL untouched; frozen tenants and hold-qty rejects; unique/FK; decode skips abort; apply rejects stale epoch and does not advance confirmed_lsn; recover drops the crash insert; indexes match visible heap; health schema and warehouse bytes.

Seeded inventory is generated at image build from `cmd/seed`. Reference entrypoint: `solution/solve.sh`.

## Local Harbor

```bash
stb harbor run -a oracle -p Terminus-Edition-3/tenant-catalog-logical-cdc-plane -o /tmp/e3-catalog
stb harbor run -a nop -p Terminus-Edition-3/tenant-catalog-logical-cdc-plane -o /tmp/e3-catalog
```

Oracle reward 1, NOP 0.
