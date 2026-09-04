# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `Q2 repair validated` → pending commit/push + QI redispatch
- Working branch: `main`
- Pull request: `none`
- Current task commit: `3ab868d35ed0897c6a0ba10c504439ee48bc6722` (pre-Q2; working tree has Q2 test repairs)
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Effective control-plane commit: `474f2b09fcda1848ef64d894a1b702be4f923b2b`
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Complexity | PASS | f2p rising with Q2 cases |
| Runtime authenticity | PASS | prior |
| Q4 Spec-Test Contract | REVISE @ 3ab868d3 | STC-UNT-001/002; Q2 tests added in working tree |
| Q6 Production Logic | PASS @ 3ab868d3 (artifact) | `5c66f2ed1c` |
| Quality Interlock | FAILED @ 3ab868d3 | run `33757931942`; do not treat as PASS |
| Oracle = 1 | PASS (working tree + prior freeze) | `jobs/2026-09-04__10-54-42` mean **1.000** after Q2 edits |
| NOP = 0 | IN_PROGRESS / prior PASS @ 3ab868d3 | awaiting post-Q2 nop |
| PRE_LLMaJ | BLOCKED | needs QI PASS on new freeze |

## Decisions that must survive chat changes

- QI run `33757931942` is NOT PASS (Q4 REVISE + collect freshness fail).
- Q2 coverage: `test_f2p_same_zone_failopen_forwards_remote_only` + CP-restart asserts restored `active_generation`, reconnect session fence, replay, stale-rev 409.
- Do not restore Begin-supersede. Do not redispatch QI on `3ab868d3` after semantic REVISE.
- Harbor oracle after Q2 edits: `2026-09-04__10-54-42` reward 1.000.

## Next action

Finish nop=0, commit Q2 test freeze + session, push main, redispatch QUALITY_INTERLOCK for the new task_commit.

## Current blocker

Awaiting nop + publish of new freeze for QI redispatch.
