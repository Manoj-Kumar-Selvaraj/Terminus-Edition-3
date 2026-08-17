# Q2 Verifier Coverage Direct Diagnostic

Artifact type: direct producer/fixer diagnostic (not a schema-v3 semantic review)

- Task: `cobol-comp3-python-equiv`
- Role: `Q2 — Verifier Coverage Repairer`
- Git-derived task SHA at start/completion: `bb2e042c45873da3f3d78836d915ddb6446debf2`
- Task files modified: `NO`
- Status: `REPAIR_PROPOSED`
- Empirical rerun required after any verifier repair: `YES`

## Requirement matrix

| REQ | Coverage | Current test evidence / note |
| --- | --- | --- |
| REQ-PUBLIC-COMMAND-SURFACE | COMPLETE | Public executable and `init-db`, `describe-layout`, `identity`, `run`, `preflight`, `audit`, `archive` surface covered. |
| REQ-CALLER-PROVIDED-PATHS | COMPLETE | Caller `--source`/`--layout` behavior covered. |
| REQ-CLI-RESULT-PROTOCOL | COMPLETE | Exit/stdout/stderr JSON protocol covered. |
| REQ-COMP3-DIGITS-PADDING | COMPLETE | Digit nibbles and zero pad covered. |
| REQ-COMP3-SIGN-DOMAIN | PARTIAL | Existing sign-domain tests; proposed explicit C-positive preservation scenario. |
| REQ-REDEFINES-STORAGE | COMPLETE | Overlay/cursor behavior covered. |
| REQ-ODO-BOUNDS | COMPLETE | Above-max rejection covered. |
| REQ-MALFORMED-RECORD-BOUNDARY | COMPLETE | Determinable malformed record boundary covered. |
| REQ-GENERATION-IDENTITY | PARTIAL | Layout digest binding covered; proposed explicit business-date identity perturbation. |
| REQ-CHECKPOINT-RESUME | COMPLETE | Identity matching and last_sequence+1 resume covered. |
| REQ-SAME-GENERATION-REPLAY | COMPLETE | Current-generation duplicate suppression covered. |
| REQ-CROSS-GENERATION-REPLAY | PARTIAL | DB allows generation-scoped uniqueness; no end-to-end second-generation replay scenario. |
| REQ-ACCEPTED-DURABILITY | COMPLETE | Accepted transaction rollback/atomicity covered. |
| REQ-REJECTED-DURABILITY | COMPLETE | Rejected transaction rollback/atomicity covered. |
| REQ-STATE-UNIQUENESS | COMPLETE | Generation/sequence uniqueness constraints covered. |
| REQ-STABLE-REJECT-CODES | PARTIAL | Stable code families covered partly; proposed durable DB+CSV verification for DECODE/TRANSFORM. |
| REQ-MOVEMENT-SHAPE | PARTIAL | Positive quantity and some endpoint constraints covered; proposed fuller contract-boundary table. |
| REQ-REASON-TYPE-COMPATIBILITY | PARTIAL | Valid receipt path covered; proposed complement matrix. |
| REQ-ITEM-POLICY | PARTIAL | Inactive item/active receipt covered; proposed unknown/max cost/precision cases. |
| REQ-WAREHOUSE-POLICY | PARTIAL | Inactive warehouse/active receipt covered; proposed unknown warehouse and fuller endpoint cases. |
| REQ-AVAILABLE-QUANTITY | COMPLETE | Over-issue rejection covered. |
| REQ-WEIGHTED-VALUATION | PARTIAL | Helper-level source valuation/transfer tests; proposed end-to-end durable outcome. |
| REQ-LEGACY-RECONCILIATION | COMPLETE | Six controls/tolerances covered. |
| REQ-DUPLICATE-MOVEMENT-SAFETY | PARTIAL | Currently combined with other corruption; proposed isolated duplicate-only state. |
| REQ-ORPHAN-EFFECT-SAFETY | PARTIAL | Currently combined with other corruption; proposed isolated orphan-only state. |
| REQ-TRANSFER-BALANCE-SAFETY | PARTIAL | Transfer value and combined imbalance coverage; proposed separate quantity/value imbalance. |
| REQ-SETTLEMENT-EFFECT-PRESENCE | COMPLETE | Missing-effect/detail corruption covered. |
| REQ-SETTLEMENT-EFFECT-KIND-UNIQUENESS | NONE | No duplicate same-kind effect scenario. |
| REQ-SETTLEMENT-POSITION-FLOORS | PARTIAL | Negative quantity covered; proposed value-only floor/boundary case. |
| REQ-PUBLICATION-GATING | PARTIAL | Failed reconciliation blocks publication; proposed more safety subclasses. |
| REQ-PUBLICATION-ATOMICITY | COMPLETE | Repeat publication/idempotent visibility coverage treated as sufficient by Q2. |
| REQ-PUBLICATION-IDEMPOTENCY-INTEGRITY | PARTIAL | Same-generation idempotence and first publication verification covered; proposed conflicting foreign-generation target. |
| REQ-PREFLIGHT-REAL-INPUTS | PARTIAL | Caller layout and historical baseline covered; proposed nonempty all-inactive catalog cases. |
| REQ-AUDIT-HEALTH-DOMAINS | PARTIAL | Several perturbations plus reachability; proposed one perturbation per named audit family. |
| REQ-ARCHIVE-INPUT-VERIFICATION | VACUOUS | Healthy archive only; proposed corrupt report/publication rejection. |
| REQ-ARCHIVE-CONTROLS-DELTAS | PARTIAL | Current archive checks control labels/fixed tokens; proposed generation-derived second-generation deltas. |
| REQ-ARCHIVE-LINEAGE-INTEGRITY | PARTIAL | Generation/source/layout/publication-manifest digests and registry evidence checked; proposed archived-byte hash verification. |
| REQ-ARCHIVE-EVENT | COMPLETE | Archive journal event covered. |
| REQ-ARCHIVE-RETENTION | COMPLETE | Positive retention horizons covered. |
| REQ-ARCHIVE-LIVE-PRESERVATION | COMPLETE | Live report/publication non-mutation covered. |
| REQ-SCHEMA-REPORT-PUBLICATION-COMPATIBILITY | PARTIAL | CLI/schema uniqueness/publication verification partially cover it; proposed public archive corruption checks. |

## Proposed scenarios

### Q2-S01 — COMP-3 sign domain — P2P
Assert a known positive signed value encodes with `C` specifically and a known C-encoded value decodes successfully, preventing a mutually consistent but undocumented pack/unpack sign convention.

### Q2-S02 — generation identity / cross-generation replay — P2P
Hold source/layout constant and change business date; generation identity must change. Process the same movement ID under both generations and verify the second generation is independently accepted with exactly one set of effects.

### Q2-S03 — stable reject codes — P2P
For `DECODE` and `TRANSFORM`, verify the documented code appears in both durable database state and generated reject CSV.

### Q2-S04 — movement shape / reason-type / item / warehouse policy — P2P
One table-driven public-processing scenario covering negative quantity; missing/forbidden endpoints; complement of documented reason/type matrix; unknown item; unknown warehouse; unit cost above `max_unit_cost`; quantity precision above `quantity_precision`; and valid active receipt/issue/transfer/adjustment cases.

### Q2-S05 — weighted valuation — F2P
Process a successful issue and transfer through the runtime against a known position whose weighted value differs from supplied movement unit cost; assert durable effects/positions use source weighted value and transfer value nets to zero.

### Q2-S06 — duplicate/orphan/transfer safety — mixed
Isolate duplicate-only, orphan-only, transfer quantity-imbalance-only, and transfer value-imbalance-only states. Each must independently make reconciliation non-passing.

### Q2-S07 — settlement uniqueness/floors/publication gating — P2P
Separately inject duplicate same-kind effect and value-only position below `-0.01`; public close/run must refuse publication. Preserve `-0.01` as the allowed boundary.

### Q2-S08 — publication idempotency/integrity — P2P
Place an internally valid publication belonging to generation B at generation A's target and attempt publication of A; it must reject rather than treat foreign valid content as idempotent A publication.

### Q2-S09 — preflight real inputs — F2P
Keep catalog rows but mark all items inactive, then separately all warehouses inactive. Each zero-active catalog must return `passed:false` / exit 2.

### Q2-S10 — audit health domains — P2P
Perturb each named audit health family separately and require the public audit evidence payload, excluding only the aggregate `passed` flag, to change materially.

### Q2-S11 — archive input verification / compatibility — P2P
After a valid run, separately corrupt a required report artifact and a published member/manifest, then invoke public `archive`; each must reject and must not record a successful verified archive event.

### Q2-S12 — archive controls/deltas / lineage integrity — P2P
Archive a second generation with materially different quantity/item/warehouse state. Verify exported controls/deltas match that generation's durable state and recorded member hashes match actual archived bytes.

## Risk assessment

- `TEST_DUPLICATION_RISK: LOW`
- `IMPLEMENTATION_COUPLING_RISK: HIGH`

Q2 observed that a significant portion of the existing verifier directly imports private `src.*` functions/classes for COMP-3, layout offsets, generation/checkpoint, policy, accounting, reconciliation, and publication. Q2 recommends new coverage prefer public CLI plus durable SQLite/report/publication observations.

## Empirical requirement

`EMPIRICAL_RERUN_REQUIRED: YES`

After any verifier repair, every new scenario must be classified against the untouched starter and Oracle. New F2P scenarios must fail untouched starter/NOP and pass Oracle; new P2P scenarios must preserve passing behavior. Then rerun the full suite and reconfirm Oracle reward 1 and NOP reward 0.

Current supplied evidence at this diagnostic point: Oracle `40 passed`; untouched/NOP `30 failed, 10 passed`.

## Completion

`GIT_DERIVED_TASK_SHA: bb2e042c45873da3f3d78836d915ddb6446debf2`

`TASK_FILES_MODIFIED: NO`
