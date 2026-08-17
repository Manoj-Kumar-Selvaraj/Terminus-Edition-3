# Q3 Spec Ambiguity Repairer — event-time-session-window-processor

```text
STATUS: REPAIR_PROPOSED
AMBIGUITIES:
- AMB_ID: AMB-IDENTICAL-RUN
  COMPETING: any second run vs second run from a clean journal/open baseline
  GRADING: digest equality fails if journal leftover is allowed
  CLARIFICATION: "From a clean journal, a second identical run..."
  ARTIFACT: instruction.md
- AMB_ID: AMB-INPUT-VS-FEED
  COMPETING: both flags as synonyms vs distinct order rules
  GRADING: --feed too-late vs --input gap close
  CLARIFICATION: --input tie-break vs --feed file order named in the work request
  ARTIFACT: instruction.md
UNRESOLVED: none material; half-open/lateness/watermark formula remain in the binding contract
```
