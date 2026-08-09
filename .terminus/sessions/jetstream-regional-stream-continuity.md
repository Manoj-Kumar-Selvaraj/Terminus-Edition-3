# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12` (draft quality-interlock validation PR)
- Current task commit: `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`
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

The second Q4 remediation does not change solver-visible production/runtime/configuration. The current verifier/test-map shape is 40 tests: exactly 30 F2P + 10 P2P across 26 mapped requirements. One reference-solution correction rejects wrong-stream publish acknowledgements. Current task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` changes only the existing hub-sequence reconciliation F2P to a schema-valid discriminator.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged; grading semantics remain discoverable from `instruction.md` plus referenced continuity contract |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | five second-cycle Q4 coverage findings addressed while F2P remains exactly 30; hub-sequence F2P now uses schema-valid existing-generation state |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity or phantom requirement |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | reference solution rejects positive acknowledgements from wrong physical stream and leaves the journal retryable |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | require fresh Preflight/Ruff/build/package evidence |
| Creator Complexity Gate | PASS_PENDING_EXACT_HEAD_RERUN | V2 discriminator workflow strict check: 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS_PENDING_EXACT_HEAD_RERUN | solver-visible production runtime unchanged; exact-head rerun required |
| Agent System / review freshness | PENDING_RERUN | this session update rebinds current task commit to `c3ee2778...` |
| Preflight/static | PENDING | current task commit `c3ee2778...` |
| Ruff verifier | PENDING | current task commit `c3ee2778...` |
| Environment/verifier build | PENDING | current task commit `c3ee2778...` |
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

The verifier/reference repair beginning at `de8efb320ade9c445963ab49edf0cd1bf5958073` addresses all five without changing solver-visible production runtime or expanding `instruction.md`:

1. Existing publish F2P rejects a positive ack from the wrong physical stream; Q5/reference solution records `ACK_STREAM_MISMATCH` and leaves `RETRY`.
2. Existing reconciliation F2P grades independence from hub aggregate delivery sequence.
3. Existing delayed-retry F2P verifies one durable effect/dispatch and one archive identity after a post-window duplicate/redelivery.
4. Existing stale-worker F2P changes fencing epoch after the first item of a two-item replay and requires the second item to be held.
5. New P2P uses the real `continuityctl` interface for plan/list replay, retention, lease acquire/renew/release, replay execution, generation approval and generation listing against isolated copied state.

## Deterministic remediation evidence

Run `31311540936` / artifact `9037536923` failed Oracle 2/40 because of verifier setup mistakes: a hub-sequence mutation violated a unique database key and the CLI P2P created a DRAFT plan then expected the active-plan listing to return it. Commit `4f5fe54b2acf8629c6582e06fd3cf3a3b097e57f` corrected those setups.

Run `31311783264`, job `93240620437`, artifact `9037606405` then proved Oracle 40/40 PASS and NOP reward 0, but NOP was only 29 F2P FAIL + 11 PASS because the reconciliation F2P still did not distinguish the inherited starter. That empirical matrix was rejected.

Commit `1e485caa0ab352f8370548d5c21425b5f54ce850` tried a synthetic confirmed generation; run `31312142740`, artifact `9037692118`, correctly failed Oracle because the fixture violated the schema's one-active-generation-per-region unique index. This was a verifier fixture defect, not product behavior.

Current commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` uses only existing confirmed east generation 1. It completes all normal east identities, advances required consumers to the contiguous 6000 origin floor, normalizes existing east hub delivery positions to unique 30001..36000 values, extends the observed high watermark, then adds three matching high-origin identities 60000..60002 at unique hub positions 50000..50002. A contract-correct reconciler compares stable identity/origin metadata and should converge with a contiguous origin floor of 6000; the inherited implementation incorrectly compares highest hub delivery position 50002 against highest origin sequence 60002 and should emit `SEQUENCE_LAG`. Ruff, py_compile and strict complexity passed before push. The temporary V2 discriminator workflow was removed immediately afterward.

## Historical provenance

- `fc137e82...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...` artifact `9035735832`: Oracle 39/39; NOP 30 F2P fail + 9 P2P pass; stale.
- `4f5fe54b...` artifact `9037606405`: Oracle 40/40; NOP 29 F2P fail + 11 pass; reward 0 but empirical matrix rejected; stale.
- `1e485caa...` artifact `9037692118`: Oracle 39/40 due invalid active-generation fixture; stale.

No historical Q4/Q6 result satisfies the current interlock.

## Current blocker

`Run fresh deterministic validation on task commit c3ee277828c2a156ecce9d335820d57b9fd2a0e0. Require strict gates, Preflight/Ruff/build, Oracle=1, NOP=0, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS. Only then refreeze and generate new Q4/Q6 packets.`

## Root-cause classification

- Owner: `Q2 Verifier Coverage Repairer` plus one `Q5 Reference Solution` correction
- Latest failure classification: `VERIFIER_HARNESS` for the invalid synthetic active-generation fixture; current V2 uses schema-valid existing-generation state

## Next action

`Inspect live PR #12 Actions on the reconciled head. If the exact 40-test matrix passes, set FROZEN_CANDIDATE for c3ee2778..., generate repository-native fresh Q4/Q6 packets, remove packet-generation helper, then rerun Q4 and Q6 in separate cold contexts.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 remain authoritative.
- Keep F2P exactly 30; current verifier is 30 F2P + 10 P2P.
- Require the empirical F2P/P2P matrix, not just Oracle/NOP aggregate rewards.
- Do not weaken solver-visible requirements or expand the natural instruction into a hidden-test checklist.
- Solver-visible production/runtime/configuration is unchanged by the second Q4 cycle.
- Current task commit is `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` unless a newer task-file commit exists.
- All Q4/Q6 results through `a57ed7e6` are historical/stale for current interlock.

## Resume rule

Resolve current task commit from Git and require `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` unless a newer task-file commit exists. Inspect live PR #12 deterministic evidence. Refreeze only after current Oracle/NOP and strict gates pass, then generate fresh packet-bound Q4/Q6 reviews.
