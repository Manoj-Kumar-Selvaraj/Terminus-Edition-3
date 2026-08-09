# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `main`
- Pull request: `#6` (merged production hardening); `#7` (merged production-policy hardening); `#8` (closed validation-only)
- Current task commit: `2c0fab5a0be9f9d3d5d01bdaba9e49c6a56ac953`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Production-authenticity policy: `1.1`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Live-state reconciliation

The last fully evidenced deterministic/review baseline predates later solver-visible task changes. Commit `ee7df06085a5b4eeaf58061e5a9e519f69d0207e` first moved the task beyond the older `eb78d72a8920348ff950a1e811e6fda773d046e5` baseline. Repository commit `2c0fab5a0be9f9d3d5d01bdaba9e49c6a56ac953` (`Final Polish payment-eod`) subsequently changed the task again, including the production-state profile and deterministic seed/data shape. Under protocol 2.1, deterministic evidence and all task-bound semantic packets/results from the older task commits remain stale for current acceptance use.

This checkpoint does not claim the latest final-polish changes are wrong. It records the provenance consequence only: the task must be deterministically revalidated on `2c0fab5a` before fresh semantic reviewer packets can support acceptance. Historical PR #6/#7/#8 evidence remains immutable diagnostic history; none of it is current PASS evidence for `2c0fab5a` merely because it passed an earlier revision.

## Current task profile

The task remains a strict production-style payment EOD restart/control-chain incident with production-scale deterministic state and a large COBOL business-program portfolio. Historical evidence from the earlier baseline measured 29 defect manifestations across six root-cause clusters, 30 F2P + 7 P2P cases, roughly 4,092 substantive solver-visible LOC, 15,012 primary payment records / 135,637 total database rows and 14 substantial COBOL programs. The later `2c0fab5a` task change materially expanded production-state requirements and seed diversity/volume, so current measurements must come from fresh strict-complexity and production-authenticity evidence rather than copying the old numbers forward.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Production Authenticity Gate | STALE | historical PR #7 run `31294714699`, job `93197811556`; predates current task commit `2c0fab5a` |
| Creator Complexity Gate | STALE | historical PR #7 run `31294714679`; predates current task commit |
| Preflight/static | STALE | historical PR #6 run `31271746650`, job `93138826901`; task changed afterward |
| Ruff verifier | STALE | historical PR #6 run `31271746650`; task/verifier evidence is not current for `2c0fab5a` |
| Oracle = 1 | STALE | historical PR #6 artifact `9025864648`, 37/37 PASS; task changed afterward |
| NOP = 0 | STALE | historical PR #6 artifact `9025864648`, 30 F2P fail + 7 P2P pass; task changed afterward |
| F2P/P2P empirical matrix | STALE | historical matrix belongs to an earlier task revision |
| Task Architect | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Verifier Engineer | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Originality & Authenticity | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Difficulty design | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Compliance pre-review | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Instruction Reviewer | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Documentation Reviewer | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Comprehensive Reviewer | STALE_PACKET | historical packet/review set is bound to an older task commit |
| Pre-LLMaJ aggregate | NOT_READY | deterministic baseline and semantic packets must be refreshed first |
| Harbor LLMaJ | NOT_RUN | requires fresh Pre-LLMaJ PASS and reusable model credential |
| GPT-5.5 difficulty ×5 | NOT_RUN | later expensive gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later expensive gate |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | combined ten-run evidence pending |
| Trial Analysis | NOT_RUN | no current official trial set |
| Final Compliance | PENDING | after model-backed evaluation |
| Final Human Quality | PENDING | after model-backed evaluation |
| Final package | PENDING | |

## Historical evidence retained

- PR #7 Production Authenticity: run `31294714699`, job `93197811556`, PASS under task commit `eb78d72a` and Production Authenticity 1.1.
- PR #7 Complexity: run `31294714679`, PASS under the prior task revision.
- PR #6 deterministic task validation: run `31271746650`, job `93138826901`, artifact `9025864648`; Oracle `37 passed`, reward `1`; NOP `30 failed, 7 passed`, reward `0`.
- PR #8 review-freshness/control-plane validation: run `31294882020`, job `93198238532`, PASS before the later final-polish task commits.
- The immutable historical packet/review directories remain provenance history and must not be overwritten or promoted to current PASS.

## Current blocker

`The current payment task is at 2c0fab5a0be9f9d3d5d01bdaba9e49c6a56ac953, while the last complete deterministic/review evidence belongs to older task revisions. Current acceptance work must resume with deterministic validation on 2c0fab5a; only after that baseline is green should fresh packet-bound semantic reviews be generated.`

The separate reusable-model credential blocker is relevant only after fresh deterministic and Pre-LLMaJ evidence exists.

## Next action

Run deterministic validation for `payment-eod-control-chain` at task commit `2c0fab5a0be9f9d3d5d01bdaba9e49c6a56ac953`: production authenticity, strict complexity, preflight/Ruff, Oracle, NOP and the F2P/P2P empirical matrix. If task-relevant files remain unchanged after those gates pass, generate a new v3 packet queue for the independent specialist and Comprehensive reviewers. Do not reuse older packets as current evidence.

## Circuit breakers

- Historical deterministic evidence after task modification: `STALE`; do not promote it back to PASS by prose.
- Historical semantic packet queue: `STALE`; generate fresh packets only after deterministic validation.
- AI/model refresh circuit breaker: `ACTIVE`; do not spend model-backed runs before fresh Pre-LLMaJ PASS.
- No task repair strategy should weaken legitimate F2P behavior merely to restore green.

## Resume rule

Resolve the current task commit from Git and require `2c0fab5a0be9f9d3d5d01bdaba9e49c6a56ac953` before relying on this checkpoint. Resume from deterministic validation, not the old Pre-LLMaJ packet queue.
