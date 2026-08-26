# Quality Interlock — sovereign-l4-load-balancer @ d7a001a9

```text
QUALITY_INTERLOCK: PENDING_REREVIEW
TASK_COMMIT: d7a001a92485de5ca3ec1bd2593648436dc3c237
ISOLATION: PROCEDURAL cold review via isolated subagents (Q4 + Q6)
Q4: REVISE (HIGH, SUFFICIENT) sovereign-l4-load-balancer-d7a001a9-spec-test-contract-661ae95ed8
Q4_PATH: .terminus/reviews/sovereign-l4-load-balancer/d7a001a9/sovereign-l4-load-balancer-d7a001a9-spec-test-contract-661ae95ed8.json
Q4_BLOCKING: F001..F007 — local repair applied (uncommitted); cold Q4 re-review required
Q4_ADVISORY: F008..F010
Q4_SUBAGENT: 7a41c644-83a3-43c4-99f7-b4db768f352d
Q6: PASS (HIGH, SUFFICIENT) sovereign-l4-load-balancer-d7a001a9-production-logic-289990f233
Q6_PATH: .terminus/reviews/sovereign-l4-load-balancer/d7a001a9/sovereign-l4-load-balancer-d7a001a9-production-logic-289990f233.json
Q6_SCOPE_HASH: 6619e4ffc9587279bcf3a95cbb208bf81c252a100b61be73b4379ca03dc99112
Q6_LOC: substantive_loc=3015; TOY LOW; PADDING LOW
Q6_SUBAGENT: 2ac77fa2-9d10-4e5e-8e1b-a97e68b31700
ORACLE: 1.0 (36/36 Harbor jobs/2026-08-22__20-40-17 post-repair)
NOP: 0.0 (10 F2P fail / 26 pass Harbor jobs/2026-08-22__20-35-34 post-repair)
RUNTIME_AUTHENTICITY: PASS (prior)
COMPLEXITY: PASS (36 tests mapped)
PRE_LLMAJ: STALE
Q8: STALE
SUBMISSION_READY: REVOKED pending cold Q4 PASS
```

**Repair summary (local, uncommitted):**

- F001: `test_f2p_least_connections_prefers_lower_load`
- F002: `test_f2p_deregistered_target_drains_existing_connection` (+ lab-event filter)
- F003: `test_f2p_passive_ejection_skips_reset_target` (+ passive failure paths in `repair.py` only)
- F004/F007: docs in `recovery.md`; tests for digest + checkpoint padding
- F005: `test_f2p_audit_exports_bounded_apply_event`
- F006: `test_f2p_status_reports_rollout_present`

**Next:** Commit repair delta, run cold isolated Q4 subagent, then refresh interlock to PASS if clean.
