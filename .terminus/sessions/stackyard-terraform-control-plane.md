# Session: stackyard-terraform-control-plane

## CREATION_RULE_CONTEXT
- CONTROL_PLANE_COMMIT: 1b42a75a40977919d567fc6d38b80cb58e17b2b7
- CREATION_PROFILE: large_system_strict
- RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md, CREATION_PIPELINE.md, PRODUCTION_AUTHENTICITY.md
- KNOWN_POLICY_CONFLICTS: none

## State
Local deterministic preflight: **oracle reward 1.0**, **NOP reward 0.0** (harbor 0.21 via `stb`).
Next: `COMPLEXITY_GATE` / independent Q4–Q6 (not self-certified from producer chat).

## Notes
- Novel vs terraform-aws-* and terraform-http-backend: product is TFC-class UI+Go+SQLite control plane.
- Oracle: solution/solve.sh copies fixed policy, audit writer, UI JS then rebuilds.
- Use `stb` / harbor ≥0.21 for `environment_mode=separate` (old `harbor 0.5.0+promptfix5` runs tests in-agent and misses pytest).
- Fixed nested SQLite list queries under `SetMaxOpenConns(1)` in store (list→get deadlock).
- Jobs: `Terminus-Edition-3/jobs/stackyard-local/2026-08-15__13-57-47` (oracle), `...__14-00-37` (nop).

## Policy-conflict ledger
(empty)
