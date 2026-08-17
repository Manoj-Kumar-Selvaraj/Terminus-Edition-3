# Quality Interlock — tenant-catalog-logical-cdc-plane @ bf0338e

```text
QUALITY_INTERLOCK: REVISE
TASK_COMMIT: bf0338e23979bd7802473064fd0e02967e3de880
Q4: REVISE (HIGH, SUFFICIENT) tenant-catalog-logical-cdc-plane-bf0338e2-spec-test-contract-6b152d7cea
Q4_PATH: .terminus/reviews/tenant-catalog-logical-cdc-plane/bf0338e2/tenant-catalog-logical-cdc-plane-bf0338e2-spec-test-contract-6b152d7cea.json
Q4_EXHAUSTIVENESS: COMPLETE; BLOCKING_FINDING_IDS Q4-ST-001..Q4-ST-005; advisory Q4-ST-006..Q4-ST-010
Q6: REVISE (HIGH, SUFFICIENT) tenant-catalog-logical-cdc-plane-bf0338e2-production-logic-711b9c2c50
Q6_PATH: .terminus/reviews/tenant-catalog-logical-cdc-plane/bf0338e2/tenant-catalog-logical-cdc-plane-bf0338e2-production-logic-711b9c2c50.json
Q6_SCOPE_HASH: 668185615d1aafcb301c53a5debe66ddd9e7014b521d9d1489c595087484f6c3
Q6_BLOCKER: Q6-LOC-FLOOR (~2734 < 3000 large_system_strict); TOY LOW; PADDING MEDIUM
Q1/Q2/Q3: producer ALIGNED notes; not self-certifying Q4
Q5: Harbor oracle 1.0 / NOP 0.0 (pre-freeze; stale after repair)
Q7: FORMAT_PASS at freeze (stale after env/test repair)
ORACLE: 1.0 (pre-repair)
NOP: 0.0 (pre-repair)
PRE_LLMAJ: BLOCKED until QUALITY_INTERLOCK_PASS
Q8: BLOCKED
HARBOR_LLMAJ: DEFERRED
DIFFICULTY_TRIALS: DEFERRED
```

## Blocking remediation owners

| ID | Owner | Fix |
| --- | --- | --- |
| Q4-ST-001 | Q1/docs + CLI surface | Document `apply --cdc PATH` in catalog-contract.md |
| Q4-ST-002 | Q2 verifier | Assert WAL `ABORT` on fail-closed reject |
| Q4-ST-003 | Q2 verifier | Strengthen inspect/empty-check no side-effect assertions |
| Q4-ST-004 | Q2 verifier | Assert health rewrite after commit/decode/apply |
| Q4-ST-005 | Q2 verifier | Assert checkpoint does not bump replica epoch |
| Q6-LOC-FLOOR | env deepen | Add ≥~300 substantive reachable catalogctl-path Go/runtime logic (not seed.sql) |
