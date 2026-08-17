The catalog plane under /app/catalog still commits on a quiet sample, but snapshot reads, unique/FK/hold checks, secondary indexes, WAL-decoded CDC, replica apply, and checkpoint redo disagree after the bounce. Repair the existing Go catalog plane; don't move catalog logic into another language or throw away the WAL protocol. Shift notes are in /app/catalog/notes/oncall.md and the bounce log is under /app/catalog/logs.

- /app/catalog/docs/catalog-contract.md is binding for visibility, commit order, constraints, indexes, decode, apply, recover, CLI, and the health/cdc/apply-report/rejects schemas. Knobs live in /app/catalog/config/catalog.json.
- Drive work through /app/catalog/bin/catalogctl. Unknown flags or an unknown command exit 2 before WAL, heap, index, replica, or slot mutation. commit requires --input. --reset-output may wipe /app/catalog/out only.
- Snapshot isolation, commit-after-WAL heap/index install, CDC-from-WAL, LSN/epoch-fenced FK-safe apply, and checkpoint redo of committed records follow the contract.
- Constraint failures fail closed: append a reject, WAL ABORT, and no heap/index install. Indexes rebuild from committed-visible rows after a successful COMMIT and after recover.
- inspect and empty-check rewrite /app/catalog/out/health.json from observed state and must not recover, decode-apply, bump epoch, or append WAL. Other successful operator commands also rewrite health.json under the contract.
- Leave /app/catalog/warehouse alone.
