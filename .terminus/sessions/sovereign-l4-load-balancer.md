# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `FROZEN_CANDIDATE` — STC-001 freeze pushed path; Q6 budget ACCEPT_RISK recorded
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
| Q4 Spec-Test Contract | REVISE @ cfcf72ba (stale for freeze) | STC-001 remediated at `a29ea18d`; needs fresh Q4 (budget 2/3 used, 1 left) |
| Q6 Production Logic | PASS artifact @ cfcf72ba (unpublished; not reusable) | role_contract_hash stale vs current; operations.md scope changed; need fresh Q6 after cancelled-claim void |
| Quality Interlock | PENDING redispatch | ACCEPT_RISK `hd_1e0e3dbff38a1c888931de5d71481322663adcb447df58cfa49a5cd367fed2a2` authorizes void of cancelled Q6 receipt 33841667900-1 |
| Oracle / NOP | PASS @ cfcf72ba | 1.000 / 0.000 — rebind after QI if freeze advances |

## Decisions that must survive chat changes

- STC-001: `GET /v1/nodes` documented in `instruction.md` + `operations.md` at freeze `a29ea18d`.
- Owner **ACCEPT_RISK** for Q6 budget exhaustion (`ACCEPT_Q6_BUDGET_EXHAUSTION_RISK`) bound to task commit `a29ea18d`; authorizes treating cancelled concurrency receipt `33841667900-1` as non-counting.
- Do not fabricate QI PASS; do not treat cancelled run as PASS.
- Prior Q4 residual ACCEPT_RISK at `38225c53` remains historical only.

## Next action

1. Push freeze + human-decision ledger + session to `origin/main`.
2. On `terminus-quality-budget`, remove `q-runs/sovereign-l4-load-balancer/q6/33841667900-1.json` under the recorded decision.
3. Redispatch AUTOMATED `QUALITY_INTERLOCK` for task commit `a29ea18d` (Q4 last slot + Q6 remaining slot).

## Current blocker

Awaiting durable budget void + QI redispatch after push.
