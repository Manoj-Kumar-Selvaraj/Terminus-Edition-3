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

The second Q4 remediation did not change solver-visible production/runtime/configuration or expand `instruction.md`. Current private verifier/test-map shape is 40 tests: exactly 30 F2P + 10 P2P across 26 mapped requirements. One Q5/reference-solution correction rejects wrong-stream publish acknowledgements. Task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` is now deterministically frozen.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged; grading semantics remain discoverable from `instruction.md` plus referenced continuity contract |
| Q2 Verifier Coverage Repair | PASS | five second-cycle Q4 coverage findings addressed; final empirical matrix proves all 30 F2P distinguish the starter and all 10 P2P preserve inherited behavior |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity or phantom requirement; no wording expansion required |
| Q5 Oracle & Runtime Repair | PASS | reference solution now rejects wrong physical-stream acknowledgements; fresh Oracle 40/40 |
| Q7 Task Format Enforcer | PASS | run `31312365548`, job `93242032230`: Preflight, Ruff and environment/verifier build PASS |
| Creator Complexity Gate | PASS | clean-head run `31312365535`; strict shape remains 5,488 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements |
| Production Authenticity Gate | PASS | clean-head run `31312365526`; solver-visible production runtime unchanged |
| Agent System / review freshness | PASS | clean-head run `31312365523`: regression, structure, freshness/commit binding and package isolation PASS |
| Preflight/static | PASS | run `31312365548`, job `93242032230` |
| Ruff verifier | PASS | run `31312365548`, job `93242032230` |
| Environment/verifier build | PASS | run `31312365548`, job `93242032230` |
| Oracle = 1 | PASS | run `31312365548`, job `93242032230`; 40/40 verifier cases pass |
| NOP = 0 | PASS | run `31312365548`, job `93242032230`; reward 0 |
| F2P/P2P empirical matrix | PASS | artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`: NOP exactly 30 F2P FAIL + 10 P2P PASS |
| Leakage/package checks | PASS | clean-head Agent-System package isolation PASS |
| FROZEN_CANDIDATE | PASS | task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` |
| Q4 Spec-Test Contract Reviewer | PENDING_FRESH_PACKET | all prior Q4 results are stale after verifier/reference changes |
| Q6 Production Logic Auditor | PENDING_FRESH_PACKET | all prior Q6 results are stale by exact task-commit binding |
| Quality Interlock | PENDING | requires fresh packet-bound Q4 + Q6 PASS with sufficient evidence |
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

The current verifier/reference revision addresses all five without changing solver-visible production runtime or expanding the natural instruction:

1. Existing publish F2P rejects a positive ack from the wrong physical stream; Q5/reference solution records `ACK_STREAM_MISMATCH` and leaves `RETRY`.
2. Existing reconciliation F2P uses complete stable identities and deliberately unrelated but schema-valid hub delivery positions; the inherited starter's aggregate-sequence dependency now fails this case.
3. Existing delayed-retry F2P verifies one durable effect/dispatch and one archive identity after a post-window duplicate/redelivery.
4. Existing stale-worker F2P changes fencing epoch after the first item of a two-item replay and requires the second item to be held.
5. New P2P uses the real `continuityctl` interface for plan/list replay, retention, lease acquire/renew/release, replay execution, generation approval and generation listing against isolated copied state.

## Deterministic evidence history

- Run `31311540936`, artifact `9037536923`: Oracle 38/40 because two verifier setup errors were discovered; rejected.
- Run `31311783264`, artifact `9037606405`: Oracle 40/40, NOP reward 0 but only 29 F2P FAIL + 11 PASS; empirical matrix rejected because hub-sequence F2P still passed starter.
- Run `31312142740`, artifact `9037692118`: Oracle 39/40 because a synthetic active-generation fixture violated the one-active-generation-per-region schema; rejected as verifier harness error.
- Current run `31312365548`, job `93242032230`, artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`: Oracle 40/40 PASS; NOP exactly 30 F2P FAIL + 10 P2P PASS. This is the accepted deterministic freeze evidence.

The workflow still fails later at reusable AI credential preparation because `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is absent. That downstream dependency occurs after current Oracle/NOP and does not invalidate the deterministic freeze; Harbor remains a later gate after Quality Interlock/Pre-LLMaJ/Q8.

## Historical semantic provenance

- `fc137e82...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `a57ed7e6...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.

All prior semantic reviews are retained only as history and are stale for current task commit `c3ee2778...`.

## Current blocker

`Generate fresh repository-native packet-bound Q4 and Q6 reviews for task commit c3ee277828c2a156ecce9d335820d57b9fd2a0e0. Run each in a separate cold reviewer context, commit exact result JSONs, validate provenance, then evaluate Quality Interlock.`

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `none`
- Evidence: `second-cycle Q4 findings are repaired and the exact deterministic matrix is green; next dependency is independent semantic review`

## Next action

`Generate fresh Q4 and Q6 packets using .terminus/new_review_packet.py for task commit c3ee2778... and state FROZEN_CANDIDATE. Commit exact generated packet bytes, remove the temporary generator, validate clean-head freshness, then run Q4 and Q6 independently. Do not claim QUALITY_INTERLOCK_PASS until both current results validate.`

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
- Solver-visible production/runtime/configuration is unchanged by the second Q4 cycle.
- Current frozen task commit is `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`.
- All Q4/Q6 results through `a57ed7e6` are historical/stale for current interlock.

## Resume rule

Resolve current task commit from Git and require `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` unless a newer task-file commit exists. Require current fresh Q4/Q6 packet results before Quality Interlock aggregation.
