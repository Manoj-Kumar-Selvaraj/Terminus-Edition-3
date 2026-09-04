# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `STC-001 remediated locally` → pending freeze + Q6 budget decision
- Working branch: `main`
- Pull request: `none`
- Current task commit: `cfcf72ba068a866afe589546700d7ae84355f689` (working tree has STC-001 docs)
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q4 Spec-Test Contract | REVISE @ cfcf72ba | STC-001 `/v1/nodes` — docs remediated in working tree |
| Q6 Production Logic | PASS artifact @ cfcf72ba | unpublished; scope will change if `operations.md` lands |
| Quality Interlock | FAIL | do not redispatch until Q6 budget decision |
| Oracle / NOP | PASS @ cfcf72ba | 1.000 / 0.000 |

## Decisions that must survive chat changes

- STC-001 fix: document `GET /v1/nodes` in `instruction.md` + `operations.md` (`node_id`, `session_id`, `connected` minimum).
- Q6 budget **2/2 exhausted** (including cancelled concurrency claims). **HUMAN_DECISION_REQUIRED** before AUTOMATED QI.
- Do not treat cancelled runs as QI PASS.

## Next action

Commit/push STC-001 docs freeze after owner confirms Q6 path: (A) accept residual risk / authorize budget exception for one more Q6, or (B) MANUAL Q6 / other policy-legal re-entry.

## Current blocker

Q6 budget exhausted — need owner decision before QI redispatch.
