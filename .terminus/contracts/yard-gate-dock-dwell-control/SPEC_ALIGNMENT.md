# SPEC_ALIGNMENT — yard-gate-dock-dwell-control

## Q1 Spec Gap Repairer

```text
STATUS: REPAIR_PROPOSED
GAPS:
- GAP_ID: G1
  GRADED_BEHAVIOR: Usage failures must not create or mutate journal, sqlite, checkpoint, or out files including rejects.jsonl.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Named /app/yard/var/events.jsonl, yard.sqlite, checkpoint.json, and /app/yard/out/rejects.jsonl on the usage fence.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
- GAP_ID: G2
  GRADED_BEHAVIOR: Parsed-but-rejected mutating commands append rejects.jsonl; usage errors do not.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Stated rejects.jsonl append for parsed rejects vs usage.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
- GAP_ID: G3
  GRADED_BEHAVIOR: Mutating commands catch up sqlite from journal events after checkpoint.last_applied_seq.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Restated journal source-of-truth and checkpoint fence catch-up without naming modules.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
- GAP_ID: G4
  GRADED_BEHAVIOR: yard.json grace minutes change window matching.
  CURRENT_DISCOVERABILITY: PARTIAL
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Changing yard_tz or grace minutes must change window matching and live clock_start.
  TEST_DETAIL_LEAKAGE_CHECK: PASS
INSTRUCTION_REQUIREMENT_COMPLETENESS: SUFFICIENT
INSTRUCTION_SHAPE: PASS
INSTRUCTION_DOC_BOUNDARY: CLEAN
CURRENT_STATE_EVIDENCE: PASS
JIRA_SLACK_HANDOFF: PASS
REVERSE_OUTLINE_RISK: LOW
UPDATE_COVERAGE_NOTE: Graded CLI/window/occupancy/chassis/hold/journal/publish behaviors remain discoverable from instruction + /app/yard/docs/yard-contract.md.
```

## Q2 Verifier Coverage Repairer

```text
STATUS: COVERED
REQUIREMENT_MATRIX:
- R_CLI: complete (unknown verb, empty event-id, missing required flags)
- R_WINDOW / R_GRACE / R_CONFIG / R_CLOCK: complete
- R_SPOT / R_MOVE / R_DOOR / R_CHASSIS: complete
- R_HOLD / R_PAUSE: complete
- R_EVENT / R_SEAL / R_CONTRACT / R_IDENTITY / R_POOL: complete
- R_WAREHOUSE / R_HEALTH / R_JOURNAL / R_MOVES: complete
- R_PRESERVE: P2P
EMPIRICAL_NOTE: Added missing-flag usage, yard.json grace mutation, sqlite-lag catch-up, and rejects.jsonl assertion on APPOINTMENT_WINDOW. Local Oracle/NOP re-run required after this pass.
```

## Q3 Spec Ambiguity Repairer

```text
STATUS: CLARIFIED
CLARIFICATIONS:
- LIVE clock_start vs drop/pickup clock_start kept as operational families, not per-visit-type walkthroughs.
- Usage vs parsed-reject split for rejects.jsonl.
- Checkpoint fence is last_applied_seq, not a full-journal replay recipe.
NOTES: Binding schemas stay in yard-contract.md. Opener no longer lists each drifted subsystem as a bug catalog.
```

SPEC_ALIGNMENT: ALIGNED
