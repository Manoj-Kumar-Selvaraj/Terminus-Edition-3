# Human-writing research — yard-gate-dock-dwell-control

Writer calibration used the local seed pack (HC-001, HC-004, HC-010, HC-016, HC-017, HC-030, CP-002, CP-004, AT-002). External corpora were not materialized; coverage is DEGRADED with controller approval. No source wording is reused.

## Task-specific information-selection profile

Opening: the yard desk drifted after a control patch and operators still use yardctl. That is the work package; do not inventory defect classes in the first sentence.

Evidence: keep shift counts, journal head, and warehouse reminder in `/app/yard/ops/handoff.txt` and `/app/yard/logs/gate-desk.log`. Point at those files.

Shared context: CLI, windows, occupancy, chassis, holds, detention, journal, and publish schemas belong in `/app/yard/docs/yard-contract.md`.

Expected outcome: grouped operational invariants (usage fence, civil time, occupancy/moves, holds/detention, journal catch-up, warehouse-isolated publish) rather than one sentence per hidden test.

## Jira/Slack handoff check

PASS after Q1 rewrite. The instruction reads as a desk repair ticket: symptom, evidence paths, binding contract, and the coupled end-state. It names graded paths in running prose.

## Reverse-outline check

LOW after regrouping. The opener no longer lists each root-cause cluster.
