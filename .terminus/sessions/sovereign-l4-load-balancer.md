# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `QUALITY_INTERLOCK` refresh required (pre-ledger; legacy first incomplete gate)
- Working branch: `main`
- Pull request: `none`
- Current task commit: `994389ded87b923ba686d1ee0c078d932a24005f`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Effective control-plane commit: `857d474d50bdd78b168bd3e013fa6927a2af81b6`
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Complexity | PASS | f2p_cases=27 |
| Runtime authenticity | PASS | prior |
| Q4 Spec-Test Contract | STALE for 994389de | last cold result `25fdcdc1ba` REVISE @ feb4d04e; Q4 is never scope-reusable; env+tests changed |
| Q4 satisfaction | STALE for 994389de | `hd_52d08988…` was bound to `38225c53` with `expires_if_task_commit_changes=true` |
| Q6 Production Logic | STALE for 994389de | `6bc7f47659` @ feb4d04e scope `d4ab8912…` ≠ current `ebe838ae…` (environment/ + solution changed) |
| Quality Interlock | STALE for 994389de | prior PASS @ 38225c53 cannot bind freeze `994389de` |
| Oracle = 1 | PASS @ 994389de (Harbor empirical; pre-ledger) | `jobs/2026-09-03__16-53-43` + `jobs/2026-09-03__17-07-47` mean **1.000** |
| NOP = 0 | PASS @ 994389de (Harbor empirical; pre-ledger) | `jobs/2026-09-03__17-00-45` mean **0.000** |
| Deterministic oracle rerun | PASS | second oracle `17-07-47` mean **1.000** |
| PRE_LLMaJ | BLOCKED | waits on current QUALITY_INTERLOCK for `994389de` |
| Harbor LLMaJ | WAIVED | author policy |
| Official ×10 | WAIVED | author policy |
| Submission readiness | REVOKED | |

## Decisions that must survive chat changes

- Prior owner residual-Q4 acceptance `hd_52d08988…` remains historical for commit `38225c53` only; it does not auto-apply to `994389de`.
- Q4 verdict at feb4d04e remains REVISE; do not restore Begin-supersede.
- Oracle/NOP green after probe delay, AbortOrphaned (no Begin-supersede), selector identity+NUL hash, EPOLLERR-only close + HUP/RDHUP→IN coalesce, drop premature RDHUP marks.
- Task freeze commit: `994389ded87b923ba686d1ee0c078d932a24005f` (not yet on `origin/main`).
- Execution ledger: absent (pre-ledger task). Do not fabricate historical StageResults; use legacy first-incomplete-gate routing until current evidence is recorded through the live invocation/result contract.
- Controller `continue` on empty ledger returns `RULE_RESOLUTION` / missing `CREATION_REQUEST` — advisory only while legacy QI refresh is the first incomplete gate.

## Next action

Authorize publish of freeze `994389de` (+ session) onto `origin/main` after reconciling local `main` (ahead 11 / behind 2), then dispatch `terminus-quality-request/...` QUALITY_INTERLOCK for task commit `994389de` (`AUTOMATED`, Q8 OFF).

## Current blocker

authorization-required — `994389de` not on `origin/main`; quality-request adapter requires `expected_repository_head == remote main` and task commit resolved from that head.
