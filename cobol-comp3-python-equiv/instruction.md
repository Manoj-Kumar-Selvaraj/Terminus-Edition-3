# Warehouse inventory cutover equivalence

Repair the inherited Python warehouse-movement cutover runtime under `/app/equiv` so it is operationally equivalent to the documented legacy batch controls.

The runtime must correctly decode the supplied layout model, including COMP-3 signs/digits, dynamic `OCCURS DEPENDING ON`, and `REDEFINES` storage; honor caller-supplied source/layout paths; validate movement/item/warehouse policy; apply weighted inventory effects atomically; checkpoint only durable progress; reject stale or changed generation resumes; reconcile every documented control; and publish reports atomically only after a successful reconciliation.

The SQLite schema and seed represent the inherited state surface. `/app/equiv/log/archive` and `/app/equiv/ops` contain operator evidence relevant to the failed cutover.

Do not replace the public CLI. `bin/equiv-eval` must continue to support `init-db`, `describe-layout`, `identity`, and `run`.
