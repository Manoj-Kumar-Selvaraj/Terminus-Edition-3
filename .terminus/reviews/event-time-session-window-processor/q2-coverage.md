# Q2 Verifier Coverage Repairer — event-time-session-window-processor

```text
STATUS: COVERED
REQUIREMENT_MATRIX:
- R_CLI: F2P unknown flags, reset+unknown, missing source
- R_EMPTY: F2P empty-check and zero-event --input
- R_GAP: F2P basic half-open close, holdout gap, config gap
- R_INPUT_ORDER: F2P unsorted --input gap close; P2P equal-time tie-break
- R_FEED_ORDER: F2P later-then-earlier too-late
- R_TENANT: F2P isolation + beta open snapshot
- R_JOURNAL: F2P seq 1..n and append prefix
- R_WATERMARK: F2P nondecreasing + first-line formula
- R_LATE: F2P too-late side output + schema; P2P late-allowed join
- R_REJECT: P2P malformed JSON and negative event_time (starter already fail-closed)
- R_IDEMPOTENT: F2P matching digests after a correct close
- R_RESTART: F2P open-session extend + journal prefix
- R_CONFIG: F2P gap and lateness knobs; P2P max duration
- R_RESET: F2P --reset-output keeps journal
- R_SCHEMA: F2P closed-session fields; P2P output paths
- R_WAREHOUSE: P2P count and untouched hash
- R_CONTRACT: P2P bin + contract formula
NEW_CASES: none after remapping unsorted --input onto R_INPUT_ORDER
F2P_NOP_FAIL_ORACLE_PASS: Harbor oracle 1.0 at 2026-08-17__12-13-37; Harbor NOP 0.0 at 2026-08-17__12-14-37
```
