# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `Q4_REVISE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `d7a001a92485de5ca3ec1bd2593648436dc3c237`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Creator Complexity Gate | PASS | `validate_task_complexity` artifact 3015 — 28 F2P / 4 P2P; large_system_strict |
| Runtime authenticity | PASS | `validate_runtime_authenticity.py` |
| Ruff verifier | PASS | ruff job 1 clean |
| Oracle = 1 | PASS | docker run 32/32 at d7a001a9 |
| NOP = 0 | PASS | docker run 10 F2P fail / 22 pass at d7a001a9 |
| Q4 Spec-Test Contract | REVISE | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/sovereign-l4-load-balancer-d7a001a9-spec-test-contract-661ae95ed8.json` — isolated subagent `7a41c644`; blocking F001..F007 |
| Q6 Production Logic | PASS | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/sovereign-l4-load-balancer-d7a001a9-production-logic-289990f233.json` — isolated subagent `2ac77fa2` |
| Quality Interlock | REVISE | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/quality-interlock.md` |
| PRE_LLMAJ aggregate | STALE | prior PASS predates independent Q4 REVISE |
| Pre-LLMaJ specialists | STALE | prior panel at d7a001a9; reopen after Q4 repair |
| Q8 simulations | STALE | prior diagnostics predates Q4 REVISE |
| Harbor LLMaJ | WAIVED | author policy (revisit if scope changes) |
| Official ×10 trials | WAIVED | author policy |
| Submission readiness | REVOKED | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/submission-ready.md` |

## Decisions that must survive chat changes

- Q4 and Q6 were re-run via isolated subagents; inline-authored Q4 PASS is void.
- Q6 independent PASS retained (3015 LOC, PADDING LOW).
- Prior COMPLETE closure is withdrawn until Q4 blocking findings F001..F007 are repaired and cold Q4 re-review passes.

## Next action

Repair verifier/spec gaps F001–F007, then re-oracle/NOP and cold Q4 re-review at `d7a001a9` (or new freeze commit if task tree changes).

## Current blocker

Independent Q4 REVISE: untested least_connections/drain/passive ejection/audit plus phantom assertions on `authority.json`, `rollout_present`, and checkpoint directory padding.
