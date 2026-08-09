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
| Q1 Spec Gap Repair | PASS | grading semantics remain discoverable from `instruction.md` plus referenced continuity contract |
| Q2 Verifier Coverage Repair | PASS | second-cycle Q4 findings addressed; empirical matrix proves all 30 F2P distinguish starter and all 10 P2P preserve inherited behavior |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity or phantom requirement |
| Q5 Oracle & Runtime Repair | PASS | reference solution rejects wrong physical-stream acknowledgements; fresh Oracle 40/40 |
| Q7 Task Format Enforcer | PASS | run `31312365548`, job `93242032230`: Preflight, Ruff and environment/verifier build PASS |
| Creator Complexity Gate | PASS | run `31312365535`: 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS | run `31312365526`; solver-visible production runtime unchanged |
| Agent System / review freshness | PENDING_CLEAN_PACKET_HEAD | final packet/session head check running/required |
| Oracle = 1 | PASS | run `31312365548`, job `93242032230`; 40/40 PASS |
| NOP = 0 | PASS | run `31312365548`, job `93242032230` |
| F2P/P2P empirical matrix | PASS | artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`: exactly 30 F2P FAIL + 10 P2P PASS on NOP |
| FROZEN_CANDIDATE | PASS | task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` |
| Q4 Spec-Test Contract Reviewer | PENDING | fresh packet `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028` committed |
| Q6 Production Logic Auditor | PENDING | fresh packet `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e` committed |
| Quality Interlock | PENDING | requires current packet-bound Q4 + Q6 PASS with sufficient evidence |
| Stage-B specialists | PENDING | after Quality Interlock |
| Comprehensive Reviewer | PENDING | after Stage-B |
| Pre-LLMaJ aggregate | PENDING | after current specialists + Comprehensive |
| Q8 GPT Perspective | PENDING | after Pre-LLMaJ PASS |
| Q8 Claude Perspective | PENDING | after Pre-LLMaJ PASS |
| Harbor LLMaJ | PENDING | reusable STB AI credential absent; later gate |
| Official difficulty/model gates | NOT_RUN | after semantic gates |
| Final package | PENDING | |

## Second Q4 remediation

Independent Q4 on `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` returned `REVISE/HIGH/SUFFICIENT`; Q6 returned `PASS/HIGH/SUFFICIENT`. Q4 identified five coverage gaps: expected-stream publish acknowledgements, hub-sequence-independent reconciliation, durable post-window dedupe outcomes, fencing revalidation during multi-item replay, and preservation of non-diagnostic recovery CLI entrypoints.

The current verifier/reference revision addresses all five without changing solver-visible production runtime or expanding the natural instruction:

1. Publish F2P rejects a positive ack from the wrong physical stream; Q5/reference solution records `ACK_STREAM_MISMATCH` and leaves `RETRY`.
2. Reconciliation F2P uses complete stable identities and unrelated but schema-valid hub delivery positions; the starter's aggregate-sequence dependency now fails.
3. Delayed-retry F2P verifies one durable effect/dispatch and one archive identity after a post-window duplicate/redelivery.
4. Stale-worker F2P changes fencing epoch after the first item of a two-item replay and requires the second item to be held.
5. A P2P uses the real `continuityctl` interface for plan/list replay, retention, lease acquire/renew/release, replay execution, generation approval and generation listing against isolated copied state.

## Accepted deterministic freeze evidence

Run `31312365548`, job `93242032230`, artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`:

- Preflight/Ruff/build PASS.
- Oracle reward 1; 40/40 PASS.
- NOP reward 0; exactly all 30 F2P FAIL and all 10 P2P PASS.
- Hub-sequence reconciliation is one of the intended NOP failures.
- Later AI-credential preparation fails because `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is absent; this occurs after deterministic validation and is not current acceptance evidence.

## Fresh Q4/Q6 packet provenance

Repository-native generator run `31312573799` completed successfully. Packet artifact `9037786272` has sha256 `6f1186e2052f0bcdb9196f8418bd796c1f3598589197ce403cdc93ff2aa7d90f`. Temporary generator removed after exact generated bytes were committed.

### Q4
- Review ID: `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028`
- Role contract hash: `696aa3da8960a5c5ee1b093d2b8bced4e3f95fba130883ee4afc58c846251832`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.packet.json`
- Result path: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.json`

### Q6
- Review ID: `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e`
- Role contract hash: `d133a8d561746bb33b8622cb3e564feccfbfe669e9e601f1d0dba95762dfb29b`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.packet.json`
- Result path: `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.json`

All prior Q4/Q6 results are historical/stale for current task commit.

## Current blocker

`Require final clean packet-head Agent-System PASS, then execute fresh Q4 and Q6 independently from the c3ee2778 packets, commit exact results, and evaluate Quality Interlock.`

## Next action

`Complete cold Q4 and Q6 reviews in separate contexts after clean packet-head freshness passes. Commit exact result JSONs to packet-declared paths. Do not claim QUALITY_INTERLOCK_PASS until both current results validate.`

## Circuit breakers

- Status: `CLEAR`
- Attempts: `0`

## Decisions that must survive chat changes

- Keep F2P exactly 30; current verifier is 30 F2P + 10 P2P.
- Require empirical test classification, not only aggregate rewards.
- Current frozen task commit is `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`.
- Only c3ee2778 packet-bound Q4/Q6 results can satisfy current interlock.

## Resume rule

Require task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`, clean packet-head Agent-System PASS, and current c3ee2778 Q4/Q6 result validation before Quality Interlock aggregation.
