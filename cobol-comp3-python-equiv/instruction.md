# Warehouse inventory cutover equivalence

- Repair the inherited warehouse-movement cutover runtime under `/app/equiv`; do not replace the public executable `/app/equiv/bin/equiv-eval`.
- Preserve `init-db`, `describe-layout`, `identity`, and `run`; also keep the supplied operator workflows `preflight`, `audit`, and `archive` working.
- Every command that accepts `--source PATH` or `--layout PATH` must use the caller-provided path rather than a hard-coded default.
- The default record model is `/app/equiv/config/movement.layout.json`; exact packed-decimal, ODO, REDEFINES, malformed-record boundary, durable-state, reconciliation, publication, CLI, and reject-code semantics are delegated to `/app/equiv/ops/runtime-contract.md`.
- The legacy equivalence values are in `/app/equiv/config/legacy.controls`; all six documented controls must be compared independently, together with the documented zero-tolerance safety controls.
- Validate movement shape, reason/type compatibility, item status/policy, warehouse status/capability, available quantity, and weighted inventory valuation before accepting a movement.
- Treat an accepted movement's processed row, all inventory effects/position updates, journal event, and checkpoint advance as one durable transaction; rejected movement durability follows the delegated contract.
- Resume only after the last durable sequence and reject source, layout, or business-date changes that do not match the checkpointed generation identity.
- A current-generation exact movement replay must not reapply inventory effects; cross-generation history is not by itself a current-generation duplicate.
- Reconciliation must block publication when any documented legacy control, transfer-balance safety control, or detailed settlement invariant fails.
- Publish a verified generation atomically and make a repeated publication of the same verified generation idempotent.
- `preflight` must consume the real source/layout, schema health, catalog, input integrity, and historical production baseline rather than treating seeded history as decorative data.
- `audit` must expose replay/recovery, checkpoint, accounting, reconciliation, inventory, quarantine, journal, registry, metric, and settlement health for the generation.
- `archive` must verify reports/publication, export controls and deltas, bind lineage/integrity evidence, write a verified archive, and record the archive event.
- Inspect `/app/equiv/log/archive` and `/app/equiv/ops` for the inherited cutover evidence before changing behavior.
- Keep the SQLite schema/state and report/publication formats compatible with the solver-visible contracts; do not bypass required constraints in application code.
