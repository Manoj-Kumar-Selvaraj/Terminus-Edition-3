# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12` (draft quality-interlock validation PR)
- Current task commit: `de8efb320ade9c445963ab49edf0cd1bf5958073`
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

The second Q4 remediation did not change solver-visible production/runtime/configuration files. It strengthened verifier coverage, added one preservation P2P, repaired one reference-solution omission for wrong-stream acknowledgements, and updated the private test map. Current strict verifier shape is 40 tests: exactly 30 F2P + 10 P2P across 26 mapped requirement groups.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged; all grading semantics remain discoverable from `instruction.md` plus referenced solver-visible continuity contract; no hidden-test checklist added |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | fresh Q4 on `a57ed7e6...` returned REVISE/HIGH/SUFFICIENT with five coverage findings; verifier repairs landed in `de8efb320ade9c445963ab49edf0cd1bf5958073` while retaining exactly 30 F2P |
| Q3 Spec Ambiguity Repair | PASS | fresh Q4 found no grading ambiguity and no phantom requirement |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | reference solution now rejects positive publish acknowledgements from the wrong physical stream and leaves the event retryable; fresh Oracle required |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | verifier changed; require fresh Preflight/Ruff/build/package evidence |
| Creator Complexity Gate | PASS | remediation workflow local strict validator and clean-head run `31311491000`: 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS | clean-head run `31311490993` PASS; solver-visible production runtime unchanged |
| Agent System / review freshness | PENDING_RERUN | run `31311491001` correctly failed because the session still named stale `a57ed7e6...`; this commit reconciles session to `de8efb320...` |
| Preflight/static | PENDING | fresh task commit `de8efb320...` |
| Ruff verifier | PENDING | fresh task commit `de8efb320...` |
| Environment/verifier build | PENDING | fresh task commit `de8efb320...` |
| Oracle = 1 | PENDING | target 40/40 PASS |
| NOP = 0 | PENDING | target exactly 30 F2P FAIL + 10 P2P PASS |
| F2P/P2P empirical matrix | PENDING | target Oracle 40/40; NOP 30 F2P fail + 10 P2P pass |
| Leakage/package checks | PENDING_FRESH_EVIDENCE | task runtime untouched; rerun exact-head checks |
| FROZEN_CANDIDATE | NOT_REACHED | previous freeze became stale when verifier/reference-solution task files changed |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | `jetstream-regional-stream-continuity-a57ed7e6-spec-test-contract-0fec10b4cd`: REVISE/HIGH/SUFFICIENT; drove this repair |
| Q6 Production Logic Auditor | STALE_PASS | `jetstream-regional-stream-continuity-a57ed7e6-production-logic-f26d6870da`: PASS/HIGH/SUFFICIENT; exact task-commit binding is now stale |
| Quality Interlock | PENDING | requires deterministic refreeze and fresh packet-bound Q4 + Q6 PASS |
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

## Second fresh Q4 result

The independent Q4 review bound to task commit `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` returned `REVISE`, confidence `HIGH`, evidence `SUFFICIENT`. It found no phantom verifier behavior and no ambiguity, but identified five remaining material coverage gaps:

1. Positive publish acknowledgement had no wrong-stream case, so the expected-physical-stream boundary was only partially graded.
2. Reconciliation claimed independence from hub aggregate delivery sequence but never perturbed that sequence while holding origin identities complete.
3. The post-duplicate-window case checked stable message id only, not durable archive/effect duplicate prevention.
4. Replay fencing was checked only stale-before-entry, not after a fence transition between replay items.
5. The instruction says not to replace existing operator entrypoints, but non-diagnostic recovery `continuityctl` generation/replay/lease/retention/execution wiring lacked interface-level coverage.

Q6 on the same `a57ed7e6...` commit independently returned `PASS/HIGH/SUFFICIENT` with no production-logic findings, but its exact-commit binding is stale after this verifier/reference-solution revision.

## Round-two Q2/Q5 remediation

Commit `de8efb320ade9c445963ab49edf0cd1bf5958073` changes only verifier files, the reference solution, and the private test map. Solver-visible production/runtime/configuration is unchanged.

- Existing F2P publish-ack case now tests a positive acknowledgement from the wrong physical stream and requires rejection, `RETRY`, and an `ACK_STREAM_MISMATCH` terminal attempt rather than `PUBLISHED`.
- Existing F2P reconciliation case completes the archive, advances all required consumers, deliberately makes hub delivery positions non-equivalent to origin sequences, and requires origin-based convergence with no synthetic sequence-lag finding.
- Existing F2P delayed-retry case now proves one durable consumer effect/dispatch and one archive identity remain after a deterministic post-window duplicate/redelivery, in addition to stable message ids.
- Existing stale-worker F2P now retains the stale-before-entry assertion and adds a two-item replay where the fence epoch changes after the first publish; the second item must be held and not published.
- Added one P2P using the real `continuityctl` entrypoint against isolated copied state to exercise `plan-replay`, `list-replay`, `retention`, `lease acquire/renew/release`, `execute-replay`, `approve-generation`, and `generations` through observable state.
- Q5/reference solution adds expected-stream acknowledgement validation and records wrong-stream acknowledgement as a retryable `ACK_STREAM_MISMATCH` failure.
- Private map is now 26 requirements, 30 F2P, 10 P2P.

The temporary remediation workflow was removed immediately after producing the task commit. Its own Ruff, py_compile, and strict complexity checks passed before push.

## Historical deterministic evidence

The prior `a57ed7e6...` freeze had Oracle 39/39 and NOP exactly 30 F2P FAIL + 9 P2P PASS in run `31305175400`, artifact `9035735832`. That evidence is now stale because the verifier and reference solution changed.

## Historical semantic provenance

- `fc137e82...` Q4: REVISE/HIGH/SUFFICIENT; Q6: PASS/HIGH/SUFFICIENT.
- `a57ed7e6...` Q4: REVISE/HIGH/SUFFICIENT; Q6: PASS/HIGH/SUFFICIENT.

All four results remain historical evidence only. No prior Q4/Q6 result may satisfy the interlock for `de8efb320...`.

## Current blocker

`Complete fresh deterministic validation for task commit de8efb320ade9c445963ab49edf0cd1bf5958073. Require strict gates, Preflight/Ruff/build, Oracle=1, NOP=0, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS. Only then refreeze and generate new Q4/Q6 packets.`

## Root-cause classification

- Owner: `Q2 Verifier Coverage Repairer` with one `Q5 Reference Solution` correction
- Classification: `VERIFIER_CONTRACT_COVERAGE`
- Evidence: `fresh Q4 REVISE on a57ed7e6 identified five explicit solver-visible behaviors that remained only partially graded; Q6 found no production-logic defect`

## Next action

`Read live PR #12 CI on the reconciled head. If deterministic evidence passes, set FROZEN_CANDIDATE for de8efb320..., generate repository-native fresh Q4 and Q6 packets, remove packet-generation helper, and rerun both reviewers in separate cold contexts. Any Oracle failure routes to Q5; any verifier-contract defect routes to Q2.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 remain authoritative.
- Keep F2P at exactly 30; current target suite is 30 F2P + 10 P2P.
- Do not weaken the solver-visible continuity contract to avoid coverage work.
- Do not expand `instruction.md` into a hidden-test checklist.
- Captured incident state remains immutable evidence; do not manufacture healthy reports.
- Current task commit is `de8efb320ade9c445963ab49edf0cd1bf5958073` unless a newer task-file commit exists.
- Current `a57ed7e6` Q4/Q6 results are stale after task revision.
- Harbor AI-credential failure is downstream of deterministic validation.

## Resume rule

Resolve current task commit from Git and require `de8efb320ade9c445963ab49edf0cd1bf5958073` unless a newer task-file commit exists. Inspect live PR #12 Actions. Refreeze only after the 40-test Oracle/NOP matrix and strict gates are current; then generate and run fresh packet-bound Q4/Q6 reviews.
