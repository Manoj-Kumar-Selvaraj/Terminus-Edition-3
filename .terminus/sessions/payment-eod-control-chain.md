# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `main`
- Pull request: `#6` (merged production hardening); `#7` (merged production-policy hardening); `#8` (closed validation-only)
- Current task commit: `ee7df06085a5b4eeaf58061e5a9e519f69d0207e`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Production-authenticity policy: `1.1`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Live-state reconciliation

The previous durable checkpoint was bound to task commit `eb78d72a8920348ff950a1e811e6fda773d046e5`. Repository commit `ee7df06085a5b4eeaf58061e5a9e519f69d0207e` (`Final Polish payment-eod`) subsequently changed solver-visible task files, including the environment, interface documentation and verifier cases. Under protocol 2.1, deterministic evidence and all task-bound semantic packets/results from `eb78d72a` are therefore stale for current acceptance use.

This checkpoint does not claim the final-polish changes are wrong. It records the required provenance consequence: the task must return to deterministic validation on `ee7df060` before new reviewer packets are generated. Historical PR #6/#7/#8 evidence remains immutable history and may be used diagnostically, but it is not current PASS evidence for `ee7df060`.

## Current task profile

The task remains a strict production-style payment EOD restart/control-chain incident with production-scale deterministic state and a large COBOL business-program portfolio. The prior baseline contained 29 defect manifestations across six root-cause clusters, 30 F2P + 7 P2P cases, roughly 4,092 substantive solver-visible LOC, 15,012 primary payment records / 135,637 total database rows and 14 substantial COBOL programs. Those historical measurements must be reconfirmed where the final-polish commit could affect the corresponding gate.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Production Authenticity Gate | STALE | historical PR #7 run `31294714699`, job `93197811556`; predates current task commit `ee7df060` |
| Creator Complexity Gate | STALE | historical PR #7 run `31294714679`; predates current task commit |
| Preflight/static | STALE | historical PR #6 run `31271746650`, job `93138826901`; task changed afterward |
| Ruff verifier | STALE | historical PR #6 run `31271746650`; verifier changed afterward |
| Oracle = 1 | STALE | historical PR #6 artifact `9025864648`, 37/37 PASS; verifier/task changed afterward |
| NOP = 0 | STALE | historical PR #6 artifact `9025864648`, 30 F2P fail + 7 P2P pass; verifier/task changed afterward |
| F2P/P2P empirical matrix | STALE | historical matrix belongs to `eb78d72a` |
| Task Architect | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Verifier Engineer | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Originality & Authenticity | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Difficulty design | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Compliance pre-review | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Instruction Reviewer | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Documentation Reviewer | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
| Comprehensive Reviewer | STALE_PACKET | post-PR #7 packet under `.terminus/reviews/payment-eod-control-chain/eb78d72a/`; task commit moved |
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
- PR #7 Complexity: run `31294714679`, PASS under the prior task commit.
- PR #6 deterministic task validation: run `31271746650`, job `93138826901`, artifact `9025864648`; Oracle `37 passed`, reward `1`; NOP `30 failed, 7 passed`, reward `0`.
- PR #8 review-freshness/control-plane validation: run `31294882020`, job `93198238532`, PASS before the later final-polish task commit.
- The immutable `eb78d72a` packet/review directories remain historical provenance and must not be overwritten or promoted to current PASS.

## Current blocker

`The final-polish task change at ee7df060 invalidated the deterministic baseline and the queued eb78d72a semantic packets. Current acceptance work must resume with deterministic validation on ee7df060; only after that baseline is green should fresh packet-bound semantic reviews be generated.`

The separate reusable-model credential blocker remains relevant only after fresh deterministic and Pre-LLMaJ evidence exists.

## Next action

Run deterministic validation for `payment-eod-control-chain` at task commit `ee7df06085a5b4eeaf58061e5a9e519f69d0207e`: production authenticity, strict complexity, preflight/Ruff, Oracle, NOP and the F2P/P2P empirical matrix. If task-relevant files remain unchanged after those gates pass, generate a new v3 packet queue for the independent specialist and Comprehensive reviewers. Do not reuse the `eb78d72a` packets as current evidence.

## Circuit breakers

- Historical deterministic evidence after task modification: `STALE`; do not promote it back to PASS by prose.
- Historical semantic packet queue: `STALE`; generate fresh packets only after deterministic validation.
- AI/model refresh circuit breaker: `ACTIVE`; do not spend model-backed runs before fresh Pre-LLMaJ PASS.
- No task repair strategy should weaken legitimate F2P behavior merely to restore green.

## Resume rule

Resolve current task commit from Git and require `ee7df06085a5b4eeaf58061e5a9e519f69d0207e` before relying on this checkpoint. Resume from deterministic validation, not the old Pre-LLMaJ packet queue.
