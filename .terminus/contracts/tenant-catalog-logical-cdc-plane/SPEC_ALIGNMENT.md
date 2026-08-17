# SPEC_ALIGNMENT — tenant-catalog-logical-cdc-plane

## Q1 Spec Gap Repairer

```text
STATUS: REPAIR_PROPOSED
GAPS:
- GAP_ID: G1
  GRADED_BEHAVIOR: Constraint rejects fail closed with rejects.jsonl + WAL ABORT and no heap/index install; indexes rebuild after successful COMMIT/recover.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Added explicit fail-closed reject and index-rebuild bullets while keeping schema detail in the binding contract.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
- GAP_ID: G2
  GRADED_BEHAVIOR: Successful operator commands rewrite health.json under the contracted schema.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Clarified that inspect/empty-check and other successful commands rewrite health.json; schemas remain contract-owned.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
INSTRUCTION_REQUIREMENT_COMPLETENESS: SUFFICIENT
INSTRUCTION_SHAPE: PASS
INSTRUCTION_DOC_BOUNDARY: CLEAN
CURRENT_STATE_EVIDENCE: PASS
JIRA_SLACK_HANDOFF: PASS
REVERSE_OUTLINE_RISK: LOW
UPDATE_COVERAGE_NOTE: Graded CLI/CDC/apply/recover/index/health behaviors remain discoverable from instruction + /app/catalog/docs/catalog-contract.md.
```

## Q2 Verifier Coverage Repairer

```text
STATUS: COVERED
REQUIREMENT_MATRIX:
- R_CLI: complete (unknown flag/command, missing --input)
- R_RESET: complete
- R_INSPECT: complete (inspect + empty-check)
- R_COMMIT: preserved via P2P install check
- R_UNIQUE / R_FK / R_FROZEN / R_HOLD / R_WRITESET: complete F2P
- R_RECOVER: complete (skip uncommitted, epoch, recovery_ok, visibility_ok)
- R_CDC: complete (skip uncommitted, WAL LSN, update before)
- R_APPLY: complete F2P + P2P report integers
- R_INDEX: complete (commit match, recover rebuild, index_ok)
- R_HEALTH / R_CHECKPOINT / R_WAREHOUSE / R_CONTRACT: P2P preservation
EMPIRICAL_NOTE: Prior Harbor oracle=1 / NOP=0 with 25 F2P failing and 9 P2P passing. No new tests added in this alignment pass.
```

## Q3 Spec Ambiguity Repairer

```text
STATUS: NO_AMBIGUITY
CLARIFICATIONS: none
NOTES: Binding schemas and protocol semantics live in catalog-contract.md; instruction states the work package and preservation constraints without prescribing repair modules.
```

SPEC_ALIGNMENT: ALIGNED
