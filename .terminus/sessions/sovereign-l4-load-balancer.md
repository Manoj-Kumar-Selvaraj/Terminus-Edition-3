# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `7b32e8ad4974a4d8012085b08d82a9b1f9ca5579`
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
| Creator Complexity Gate | PASS | `validate_task_complexity` @ 7b32e8ad — substantive_loc≈3924, f2p_cases=27 |
| Runtime authenticity | PASS | `validate_runtime_authenticity.py` PASS @ 7b32e8ad |
| Ruff verifier | PENDING | recheck with verifier edits |
| Oracle = 1 | STALE | Harbor evidence pre-dates 7b32e8ad; local/Harbor revalidate still needed |
| NOP = 0 | STALE | same |
| Q4 Spec-Test Contract | REVISE | `.terminus/reviews/sovereign-l4-load-balancer/7b32e8ad/sovereign-l4-load-balancer-7b32e8ad-spec-test-contract-19bf052a7a.json` — subagent `b0fbb074`; budget 3/3 |
| Q6 Production Logic | PASS | `.terminus/reviews/sovereign-l4-load-balancer/7b32e8ad/sovereign-l4-load-balancer-7b32e8ad-production-logic-00b7dc11e8.json` — subagent `4f6c8043` (reuse if env unchanged) |
| Quality Interlock | REVISE | Q4 REVISE blocks; Q6 PASS held |
| PRE_LLMaJ aggregate | STALE | blocked |
| Pre-LLMaJ specialists | STALE | blocked |
| Q8 simulations | STALE | blocked |
| Harbor LLMaJ | WAIVED | author policy |
| Official ×10 trials | WAIVED | author policy |
| Submission readiness | REVOKED | awaiting interlock PASS |

## Decisions that must survive chat changes

- Cold Q4+Q6 at `13ffb6b2` both REVISE. Remediation completed by subagents `94a054c1` (Q4) and `f8e5c402` (Q6); case-id consolidation + repair.py by `0266be2f`.
- Mechanical LOC ~3924; f2p_cases consolidated to 27. Do not treat producer claims as Q4/Q6 PASS.
- Prior Q6 PASS @ `d7a001a9` remains STALE.

## Next action

1. Q2/Q3: close Q4-B01..B06 (prefer tests/docs-only to preserve Q6 scope hash).
2. Keep f2p_cases in 25–30 (reshape/share case_ids; use P2P for inventory if possible).
3. Q4 durable budget is 3/3 — after remediation, do **not** auto-dispatch a 4th ordinary cold Q4; route residual satisfaction (CHAT_HUMAN_RISK_ACCEPTANCE / closure) or confirm budget policy before another Q4.

## Current blocker

Q4 REVISE @ 7b32e8ad (vacuous CURRENT/checkpoint tests, metrics contradiction, fail_open unhealthy untested, inventory content, connection-view ambiguity).
