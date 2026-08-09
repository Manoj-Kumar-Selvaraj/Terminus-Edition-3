# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12` (draft quality-interlock validation PR)
- Current task commit: `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Production-authenticity policy: `1.1`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Current task profile

This remains the `large_system_strict` three-domain NATS JetStream continuity task. Solver-visible runtime/configuration remains 5,488 substantive LOC with 12,000 deterministic primary telemetry events, seven root-cause clusters, 26 interrelated manifestations, 28 causal edges, 11 cross-cluster pairs and 11 affected components.

The second Q4 remediation does not change solver-visible production/runtime/configuration. The current verifier/test-map shape is 40 tests: exactly 30 F2P + 10 P2P across 26 mapped requirements. One reference-solution correction rejects wrong-stream publish acknowledgements. Commit `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f` contains only two verifier setup corrections after the first fresh Oracle exposed test-construction errors.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged; grading semantics remain discoverable from `instruction.md` plus referenced continuity contract |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | five second-cycle Q4 coverage findings addressed while F2P remains exactly 30 |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity or phantom requirement |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | reference solution rejects positive acknowledgements from wrong physical stream and leaves the journal retryable |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | require fresh Preflight/Ruff/build/package evidence |
| Creator Complexity Gate | PASS_PENDING_EXACT_HEAD_RERUN | remediation/test-setup workflows both report strict PASS: 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS_PENDING_EXACT_HEAD_RERUN | solver-visible production runtime unchanged; exact-head rerun required |
| Agent System / review freshness | PENDING_RERUN | this commit reconciles session to current task commit |
| Preflight/static | PENDING | current task commit `4f5fe54b...` |
| Ruff verifier | PENDING | current task commit `4f5fe54b...` |
| Environment/verifier build | PENDING | current task commit `4f5fe54b...` |
| Oracle = 1 | PENDING | target 40/40 PASS |
| NOP = 0 | PENDING | target exactly 30 F2P FAIL + 10 P2P PASS |
| F2P/P2P empirical matrix | PENDING | target Oracle 40/40; NOP 30 F2P fail + 10 P2P pass |
| Leakage/package checks | PENDING_FRESH_EVIDENCE | rerun exact-head checks |
| FROZEN_CANDIDATE | NOT_REACHED | all older freezes are stale after verifier/reference changes |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | `a57ed7e6` result REVISE/HIGH/SUFFICIENT drove current repair |
| Q6 Production Logic Auditor | STALE_PASS | `a57ed7e6` result PASS/HIGH/SUFFICIENT; exact task binding stale |
| Quality Interlock | PENDING | requires deterministic refreeze then fresh packet-bound Q4 + Q6 PASS |
| Task Architect | PENDING | after Quality Interlock |
| Verifier Engineer | PENDING | after Quality Interlock |
| Originality & Authenticity | PENDING | after Quality Interlock |
| Difficulty design | PENDING | after Quality Interlock |
| Compliance pre-review | PENDING | after Quality Interlock |
| Instruction Reviewer | PENDING | after Quality Interlock |
| Documentation Reviewer | PENDING | after Quality Interlock |
| Comprehensive Reviewer | PENDING | after Stage-B |
| Pre-LLMaJ aggregate | PENDING | after current specialists + Comprehensive |
| Q8 GPT Perspective | PENDING | after Pre-LLMaJ PASS |
| Q8 Claude Perspective | PENDING | after Pre-LLMaJ PASS |
| Harbor LLMaJ | PENDING | downstream reusable STB AI credential still absent |
| GPT-5.5 difficulty ×5 | NOT_RUN | later official gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later official gate |
| Combined difficulty ×10 | NOT_RUN | later official gate |
| Per-test solvability 1/10 | NOT_RUN | later official gate |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | |

## Second Q4 review and remediation

Independent Q4 on `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` returned `REVISE/HIGH/SUFFICIENT`; independent Q6 returned `PASS/HIGH/SUFFICIENT`. Q4 found five remaining coverage gaps: expected-stream publish acknowledgements, hub-sequence-independent reconciliation, durable post-window dedupe outcomes, fencing revalidation during multi-item replay, and preservation of non-diagnostic recovery CLI entrypoints.

The verifier/reference repair in `de8efb320ade9c445963ab49edf0cd1bf5958073` addresses all five without changing solver-visible production runtime or expanding `instruction.md`:

1. Existing publish F2P now rejects a positive ack from the wrong physical stream; Q5/reference solution records `ACK_STREAM_MISMATCH` and leaves `RETRY`.
2. Existing reconciliation F2P perturbs hub delivery sequence while preserving complete stable identities and consumer convergence.
3. Existing delayed-retry F2P verifies one durable effect/dispatch and one archive identity after a post-window duplicate/redelivery.
4. Existing stale-worker F2P now changes fencing epoch after the first item of a two-item replay and requires the second item to be held.
5. New P2P uses the real `continuityctl` interface for plan/list replay, retention, lease acquire/renew/release, replay execution, generation approval and generation listing against isolated copied state.

The first full Oracle attempt for `de8efb320...` (run `31311540936`, artifact `9037536923`) failed 2/40 because of verifier setup errors rather than product behavior: the hub-sequence mutation collided with a globally unique DB key, and the CLI P2P created a DRAFT plan then expected the active-plan listing to return it. Commit `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f` corrects only those setups: hub positions are moved to a non-colliding high range, and the CLI-created replay plan is approved before active listing. Ruff, py_compile and strict complexity passed before that test-only commit was pushed.

## Historical provenance

- `fc137e82...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...` deterministic artifact `9035735832`: Oracle 39/39, NOP 30 F2P fail + 9 P2P pass; stale after current verifier changes.

No historical Q4/Q6 result satisfies the current interlock.

## Current blocker

`Run fresh deterministic validation on task commit 4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f. Require strict gates, Preflight/Ruff/build, Oracle=1, NOP=0, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS. Only then refreeze and generate new Q4/Q6 packets.`

## Root-cause classification

- Owner: `Q2 Verifier Coverage Repairer` plus one `Q5 Reference Solution` correction
- Current failed-boundary classification: `VERIFIER_HARNESS` for the two corrected test setups; no new runtime/contract defect established

## Next action

`Inspect live PR #12 Actions on the reconciled head. If the 40-test deterministic matrix passes, set FROZEN_CANDIDATE for 4f5fe54b..., generate repository-native fresh Q4/Q6 packets, remove packet-generation helper, then rerun Q4 and Q6 in separate cold contexts.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 remain authoritative.
- Keep F2P exactly 30; current verifier is 30 F2P + 10 P2P.
- Do not weaken solver-visible requirements to avoid coverage work.
- Do not expand the natural instruction into a hidden-test checklist.
- Solver-visible production/runtime/configuration is unchanged by the second Q4 cycle.
- Current task commit is `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f` unless a newer task-file commit exists.
- All Q4/Q6 results through `a57ed7e6` are historical/stale for current interlock.

## Resume rule

Resolve current task commit from Git and require `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f` unless a newer task-file commit exists. Inspect live PR #12 deterministic evidence. Refreeze only after current Oracle/NOP and strict gates pass, then generate fresh packet-bound Q4/Q6 reviews.
