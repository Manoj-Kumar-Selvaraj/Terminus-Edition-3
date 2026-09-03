# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `PRE_LLMAJ` reopen after deterministic rebind
- Working branch: `main`
- Pull request: `none`
- Current task commit: `994389ded87b923ba686d1ee0c078d932a24005f`
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Complexity | PASS | f2p_cases=27 |
| Runtime authenticity | PASS | prior |
| Q4 Spec-Test Contract | REVISE @ feb4d04e | `25fdcdc1ba` — verdict retained |
| Q4 satisfaction | PASS | `CHAT_HUMAN_RISK_ACCEPTANCE` `hd_52d08988c7e95cca7d46190e08a2109044ae2fce03acb4ae2ffb1cf72bf7d054` |
| Q6 Production Logic | PASS @ feb4d04e | `6bc7f47659` (scope-reuse review needed for oracle-fix commit 994389de) |
| Quality Interlock | PASS @ 38225c53 | `.terminus/reviews/sovereign-l4-load-balancer/38225c53/quality-interlock.md` — may need refresh for 994389de |
| Oracle = 1 | PASS @ 994389de working tree | Harbor `jobs/2026-09-03__16-53-43` + `jobs/2026-09-03__17-07-47` mean **1.000** |
| NOP = 0 | PASS @ 994389de working tree | Harbor `jobs/2026-09-03__17-00-45` mean **0.000** |
| Deterministic oracle rerun | PASS | second oracle `17-07-47` mean **1.000** |
| PRE_LLMaJ | OPEN | reopen on freeze `994389de` |
| Harbor LLMaJ | WAIVED | author policy |
| Official ×10 | WAIVED | author policy |
| Submission readiness | REVOKED | |

## Decisions that must survive chat changes

- Owner accepted residual Q4 risk for `Q4-UNT-SOURCE-HASH-ORDER`, `Q4-UNT-ZONE-LOCAL-PREFERRED`, `Q4-VAC-SEQ-REUSE-QUORUM` via chat decision `hd_52d08988…`.
- Q4 verdict remains REVISE; interlock Q4 side satisfied by `CHAT_HUMAN_RISK_ACCEPTANCE`.
- Oracle/NOP green after probe delay, AbortOrphaned (no Begin-supersede), selector identity+NUL hash, EPOLLERR-only close + HUP/RDHUP→IN coalesce, drop premature RDHUP marks.
- Task freeze commit: `994389ded87b923ba686d1ee0c078d932a24005f`.

## Next action

Resume CI orchestrator / Pre-LLMaJ on task commit `994389de` (oracle×2=1, nop=0 empirically recorded).

## Current blocker

none — Pre-LLMaJ reopen in progress
