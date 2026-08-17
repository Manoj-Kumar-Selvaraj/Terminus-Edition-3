# Q1 Spec Gap Repairer — event-time-session-window-processor

```text
STATUS: REPAIR_PROPOSED
GAPS:
- GAP_ID: GAP-CLI-MODES
  GRADED_BEHAVIOR: --input uses event-time tie-break; --feed preserves file order; --reset-output must not clear journal/open state
  CURRENT_DISCOVERABILITY: PARTIAL (CLI details lived only in session-contract.md)
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: Named --input/--feed/--reset-output in the work request without fixture values
  TEST_DETAIL_LEAKAGE_CHECK: PASS
- GAP_ID: GAP-CLEAN-REPLAY
  GRADED_BEHAVIOR: Idempotent digests require a clean journal/open baseline
  CURRENT_DISCOVERABILITY: PARTIAL ("second identical run")
  NATURAL_ARTIFACT: instruction.md
  REPAIR_TEXT: "From a clean journal, a second identical run..."
  TEST_DETAIL_LEAKAGE_CHECK: PASS
INSTRUCTION_REQUIREMENT_COMPLETENESS: SUFFICIENT
INSTRUCTION_SHAPE: PASS
INSTRUCTION_DOC_BOUNDARY: CLEAN
CURRENT_STATE_EVIDENCE: PASS
JIRA_SLACK_HANDOFF: PASS
REVERSE_OUTLINE_RISK: LOW
PRIVATE_COVERAGE_NOTE: Remaining schemas/watermark formula/seq stay in /app/sessions/docs/session-contract.md by design.
```
