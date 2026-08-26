# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `FROZEN_CANDIDATE`
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
| Oracle = 1 | PASS | Harbor `jobs/2026-08-22__20-40-17` — 36/36 after Q4 repair |
| NOP = 0 | PASS | Harbor `jobs/2026-08-22__20-35-34` — 10 F2P fail / 26 pass |
| Q4 Spec-Test Contract | PENDING_REREVIEW | blocking F001..F007 repaired locally; cold subagent re-review required |
| Q6 Production Logic | PASS | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/sovereign-l4-load-balancer-d7a001a9-production-logic-289990f233.json` — isolated subagent `2ac77fa2` |
| Quality Interlock | PENDING | Q4 fixes applied; await cold Q4 re-review |
| PRE_LLMAJ aggregate | STALE | prior PASS predates independent Q4 REVISE |
| Pre-LLMaJ specialists | STALE | prior panel at d7a001a9; reopen after Q4 repair |
| Q8 simulations | STALE | prior diagnostics predates Q4 REVISE |
| Harbor LLMaJ | WAIVED | author policy (revisit if scope changes) |
| Official ×10 trials | WAIVED | author policy |
| Submission readiness | REVOKED | `.terminus/reviews/sovereign-l4-load-balancer/d7a001a9/submission-ready.md` |

## Decisions that must survive chat changes

- Q4 and Q6 were re-run via isolated subagents; inline-authored Q4 PASS is void.
- Q6 independent PASS retained (3015 LOC, PADDING LOW).
- Q4 blocking findings F001–F007 addressed: four new F2P tests, docs for `authority.json`/`accepted_digest`, `rollout_present`, `/v1/audit`, and `generation-%020d` padding; passive ejection wired in `repair.py` only (starter tree restored).
- Oracle 36/36 and NOP 10 F2P fail confirmed after repair (`jobs/2026-08-22__20-40-17`, `jobs/2026-08-22__20-35-34`).

## Next action

Commit Q4 repair delta (uncommitted), then run cold isolated Q4 subagent re-review and refresh quality interlock.

## Current blocker

Cold Q4 re-review not yet executed on the repaired verifier/docs contract.
