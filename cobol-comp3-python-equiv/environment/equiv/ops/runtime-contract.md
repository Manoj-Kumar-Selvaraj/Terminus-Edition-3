# Warehouse cutover runtime contract

This file is solver-visible operational interface documentation for `/app/equiv/bin/equiv-eval` and the inherited SQLite/report state.

## Record and layout contract

- `/app/equiv/config/movement.layout.json` is the supplied default layout. Every CLI command that accepts `--layout PATH` must parse and use the caller-provided path; it must not silently substitute the default layout.
- COMP-3 digit nibbles must be decimal `0` through `9`. When an even number of decimal digits requires a leading storage nibble, that pad nibble must be zero.
- Signed COMP-3 accepts sign nibble `C` for non-negative values and `D` for negative values. Signed fields do not accept unsigned sign `F`. Unsigned COMP-3 requires sign nibble `F` and cannot encode a negative value.
- `REDEFINES` occupies the target field's storage and does not advance the owning record cursor a second time.
- `OCCURS DEPENDING ON` uses the decoded controlling value and rejects a count outside the field's declared `0..occurs` bound.
- If a malformed record's complete boundary is determinable from the layout and available bytes, the reject/error `byte_offset` is the record start and `byte_length` is the full layout-derived record length even when decoding fails before the end. If the boundary is indeterminate because required framing bytes are unavailable, `byte_length` is `0`.

## Durable processing contract

- A generation identity is a function of source SHA-256, layout SHA-256, and business date. A change in any of those three inputs is a different generation and cannot resume a checkpoint from the prior identity.
- A checkpoint stores the complete source/layout/date fingerprint. Resume begins at `last_sequence + 1`; the movement at `last_sequence` is already durable and must not be reapplied.
- For one accepted movement, the processed row, every inventory effect, every inventory-position update, the event-journal row, and the checkpoint advance are one SQLite transaction. An exception before commit must leave none of those changes durable.
- For one rejected movement, the reject row, processed-row status when applicable, event-journal row, and checkpoint advance are one SQLite transaction.
- `processed_movements` owns unique `(generation_id, movement_id)` and unique `(generation_id, sequence)` identities. `rejects` owns a unique `(generation_id, sequence)` identity. These are restart/race safety constraints, not presentation details.
- Stable reject codes written to the operational reject CSV/database include `DECODE`, `TRANSFORM`, `ACCOUNTING`, `QUANTITY`, `TRANSFER_LOOP`, `ITEM_INACTIVE`, and `WAREHOUSE_INACTIVE`. Human-readable exception wording is not a stable interface.

## Reconciliation and publication contract

- `/app/equiv/config/legacy.controls` defines six legacy equivalence controls: `processed_count`, `accepted_count`, `rejected_count`, `effect_count`, `net_quantity`, and `net_value`. Each is compared independently to the generation's actual state. Quantity tolerance is `0.0001`; value tolerance is `0.01`; count tolerances are zero.
- Additional safety controls require zero duplicate movement identities, zero orphan effects, and zero unbalanced transfer pairs. A transfer is balanced only when its `TRANSFER_OUT` and `TRANSFER_IN` effects net to zero quantity and zero value for that movement.
- Publication is allowed only after all legacy and safety reconciliation controls pass and detailed settlement checks are clean. The visible generation directory is promoted atomically from a staging directory.
- Re-running publication for the same generation is idempotent when the existing manifest belongs to that generation and verifies successfully; a conflicting or corrupt existing publication is an error.

## CLI and operator workflows

- Successful commands emit one JSON object to stdout and return exit code `0`. A completed operational check whose JSON contains `"passed": false` returns exit code `2`. Runtime/input exceptions emit one JSON `error` object to stderr and return exit code `2`.
- `preflight` consumes schema health, source framing/profile, the 15,000-row historical movement baseline, catalog scale, input integrity, batch-window state, authorization/safety state, and recovery state. The historical seed is operational evidence and must influence this workflow.
- `audit` reports replay/recovery health, checkpoint gaps, control state, reconciliation findings, inventory invariants, quarantine integrity, event-journal integrity, publication registry state, operational metrics, and settlement state.
- `archive` verifies report/publication contracts, exports controls and deltas, records publication registry and lineage/integrity evidence, creates a verified generation archive, records an archive journal event, and reports retention policy.
