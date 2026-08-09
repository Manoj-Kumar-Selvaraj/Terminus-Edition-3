# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
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

This is a `large_system_strict` three-domain NATS JetStream continuity task. Solver-visible runtime/configuration remains 5,488 substantive LOC with 12,000 deterministic primary telemetry events, seven root-cause clusters, 26 interrelated manifestations, 28 causal edges, 11 cross-cluster pairs and 11 affected components.

The second Q4 remediation did not change solver-visible production/runtime/configuration or expand `instruction.md`. Current private verifier/test-map shape is 40 tests: exactly 30 F2P + 10 P2P across 26 mapped requirements. One Q5/reference-solution correction rejects wrong-stream publish acknowledgements. Task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` is deterministically frozen.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged; grading semantics remain discoverable from `instruction.md` plus referenced continuity contract |
| Q2 Verifier Coverage Repair | PASS | second-cycle Q4 findings addressed; empirical matrix proves all 30 F2P distinguish the starter and all 10 P2P preserve inherited behavior |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity or phantom requirement; no wording expansion required |
| Q5 Oracle & Runtime Repair | PASS | reference solution rejects wrong physical-stream acknowledgements; fresh Oracle 40/40 |
| Q7 Task Format Enforcer | PASS | run `31312365548`, job `93242032230`: Preflight, Ruff and environment/verifier build PASS |
| Creator Complexity Gate | PASS | clean-head run `31312365535`; 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS | clean-head run `31312365526`; solver-visible production runtime unchanged |
| Agent System / review freshness | PASS_PENDING_PACKET_HEAD_CHECK | run `31312365523` passed before current packets; rerun required after packet commit/removal cleanup |
| Preflight/static | PASS | run `31312365548`, job `93242032230` |
| Ruff verifier | PASS | run `31312365548`, job `93242032230` |
| Environment/verifier build | PASS | run `31312365548`, job `93242032230` |
| Oracle = 1 | PASS | run `31312365548`, job `93242032230`; Oracle 40/40 |
| NOP = 0 | PASS | run `31312365548`, job `93242032230` |
| F2P/P2P empirical matrix | PASS | artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`: NOP exactly 30 F2P FAIL + 10 P2P PASS |
| Leakage/package checks | PASS_PENDING_PACKET_HEAD_CHECK | rerun Agent-System package isolation after packet commit |
| FROZEN_CANDIDATE | PASS | task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` |
| Q4 Spec-Test Contract Reviewer | PENDING | fresh packet `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028` committed |
| Q6 Production Logic Auditor | PENDING | fresh packet `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e` committed |
| Quality Interlock | PENDING | requires current packet-bound Q4 + Q6 PASS with sufficient evidence |
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

## Second Q4 remediation

Independent Q4 on `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` returned `REVISE/HIGH/SUFFICIENT`; Q6 returned `PASS/HIGH/SUFFICIENT`. Q4 identified five remaining coverage gaps: expected-stream publish acknowledgements, hub-sequence-independent reconciliation, durable post-window dedupe outcomes, fencing revalidation during multi-item replay, and preservation of non-diagnostic recovery CLI entrypoints.

The current verifier/reference revision addresses all five without changing solver-visible production runtime or expanding the natural instruction:

1. Existing publish F2P rejects a positive ack from the wrong physical stream; Q5/reference solution records `ACK_STREAM_MISMATCH` and leaves `RETRY`.
2. Existing reconciliation F2P uses complete stable identities and deliberately unrelated but schema-valid hub delivery positions; the inherited starter's aggregate-sequence dependency now fails this case.
3. Existing delayed-retry F2P verifies one durable effect/dispatch and one archive identity after a post-window duplicate/redelivery.
4. Existing stale-worker F2P changes fencing epoch after the first item of a two-item replay and requires the second item to be held.
5. New P2P uses the real `continuityctl` interface for plan/list replay, retention, lease acquire/renew/release, replay execution, generation approval and generation listing against isolated copied state.

## Accepted deterministic freeze evidence

Current validation run `31312365548`, job `93242032230`, artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`:

- Preflight PASS.
- Ruff verifier PASS.
- Docker/STB environment and verifier build PASS.
- Oracle reward 1; all 40 verifier tests PASS.
- NOP reward 0; exactly all 30 `test_f2p_*` cases FAIL and all 10 `test_p2p_*` cases PASS.
- The hub-sequence reconciliation F2P is now one of the 30 intended NOP failures.
- Later reusable-AI-credential preparation fails because `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is absent; that downstream dependency occurs after valid Oracle/NOP and does not invalidate deterministic freeze.

Rejected historical attempts remain documented in Git/Actions but are not acceptance evidence: `31311540936` (2 verifier fixture failures), `31311783264` (NOP only 29/11 despite reward 0), and `31312142740` (invalid second active-generation fixture).

## Fresh Q4/Q6 packet provenance

Repository-native generator run `31312573799` completed successfully. Packet artifact `9037786272` has sha256 `6f1186e2052f0bcdb9196f8418bd796c1f3598589197ce403cdc93ff2aa7d90f`. The temporary packet-generator workflow was removed after the exact generated packet bytes were committed.

### Q4

- Review ID: `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028`
- Task commit: `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`
- Role: `Spec-Test Contract Reviewer`
- Role contract hash: `696aa3da8960a5c5ee1b093d2b8bced4e3f95fba130883ee4afc58c846251832`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.packet.json`
- Expected result: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.json`

### Q6

- Review ID: `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e`
- Task commit: `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`
- Role: `Production Logic Auditor`
- Role contract hash: `d133a8d561746bb33b8622cb3e564feccfbfe669e9e601f1d0dba95762dfb29b`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.packet.json`
- Expected result: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.json`

## Historical semantic provenance

- `fc137e82...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.

All prior results are historical/stale and cannot satisfy the current interlock.

## Current blocker

`Run fresh Q4 and Q6 independently using the committed c3ee2778 packet files. Commit each exact result JSON to its declared review_output_path. Validate result provenance and only then evaluate QUALITY_INTERLOCK_PASS.`

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `none`
- Evidence: `deterministic freeze and fresh reviewer packets are current; next dependency is independent semantic review`

## Next action

`Complete cold Q4 and Q6 reviews for c3ee2778 in separate contexts, commit exact result JSONs, then resume Quality Interlock aggregation. If either returns REVISE, route only its concrete findings to the responsible producer and repeat affected deterministic/provenance gates.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 remain authoritative.
- Keep F2P exactly 30; current verifier is 30 F2P + 10 P2P.
- Require the empirical F2P/P2P matrix, not only aggregate rewards.
- Do not weaken solver-visible requirements or expand `instruction.md` into a hidden-test checklist.
- Current frozen task commit is `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`.
- Only the fresh c3ee2778 Q4/Q6 packets may produce current interlock evidence.

## Resume rule

Resolve current task commit from Git and require `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` unless a newer task-file commit exists. Validate committed c3ee2778 Q4/Q6 results before Quality Interlock aggregation.
