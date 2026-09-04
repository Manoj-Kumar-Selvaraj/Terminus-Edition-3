# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `QUALITY_INTERLOCK` collect failed after successful Q4+Q6 execute
- Working branch: `main`
- Pull request: `none`
- Current task commit: `a29ea18dfdfb4c1177cdfdede7065f811d889429`
- Creation profile: `large_system_strict`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q4 Spec-Test Contract | EXECUTED @ a29ea18d (unpublished) | run 33847572952 q4 job success; not on main |
| Q6 Production Logic | EXECUTED @ a29ea18d (unpublished) | run 33847572952 q6 job success; not on main |
| Quality Interlock | FAIL (collect) | Persist: Unexpected lifecycle mutations on dir `a29ea18d/`; record skipped |
| Oracle / NOP | PASS @ cfcf72ba | 1.000 / 0.000 |

## Decisions that must survive chat changes

- STC-001 freeze `a29ea18d` on origin/main.
- Owner ACCEPT_RISK `hd_1e0e3dbff38a1c888931de5d71481322663adcb447df58cfa49a5cd367fed2a2` voided cancelled Q6 receipt 33841667900-1.
- Do not fabricate QI PASS. Do not redispatch AUTOMATED QI while durable budgets are exhausted after this run.
- Collect bug: persist treats untracked review directory path as unexpected mutation.

## Next action

1. `gh auth login` then download artifacts from run 33847572952.
2. Publish exact Q4+Q6 packet/result for a29ea18d to main (no new budget claims).
3. Canonical QUALITY_INTERLOCK record on that evidence commit.

## Current blocker

Reviews unpublished; artifact download needs GitHub CLI auth. Budgets re-claimed by successful Q4/Q6 execute.
