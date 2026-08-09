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

## Current task profile

`large_system_strict`; 5,488 substantive solver-visible runtime/config LOC; 12,000 deterministic primary telemetry events; seven root-cause clusters; 26 interrelated manifestations; 28 causal edges; 11 cross-cluster pairs; 11 affected components. Current private verifier/test-map shape: 40 tests = exactly 30 F2P + 10 P2P across 26 requirements. Solver-visible production/runtime/configuration and natural `instruction.md` are unchanged by the second Q4 remediation.

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | solver-visible instruction + referenced continuity contract remain authoritative |
| Q2 Verifier Coverage Repair | PASS | all second-cycle Q4 findings covered; empirical 30/10 matrix current |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 found no ambiguity/phantom requirement |
| Q5 Oracle & Runtime Repair | PASS | wrong-stream positive ack reference behavior corrected |
| Q7 Task Format Enforcer | PASS | run `31312365548`, job `93242032230`: Preflight/Ruff/build PASS |
| Creator Complexity Gate | PASS | run `31312365535` |
| Production Authenticity Gate | PASS | run `31312365526` |
| Agent System / review freshness | PENDING_CLEAN_PACKET_HEAD | must pass after committed c3ee2778 packets/session anchor |
| Oracle | PASS | 40/40 in run `31312365548` |
| NOP | PASS | reward 0; exactly 30 F2P FAIL + 10 P2P PASS |
| F2P/P2P empirical matrix | PASS | artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1` |
| FROZEN_CANDIDATE | PASS | task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` |
| Q4 | PENDING | `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028` |
| Q6 | PENDING | `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e` |
| Quality Interlock | PENDING | current Q4 + Q6 PASS required |
| Later Stage-B/Comprehensive/Pre-LLMaJ/Q8/model/package gates | PENDING | after Quality Interlock |

## Accepted deterministic evidence

Run `31312365548`, job `93242032230`, artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1` is the current freeze evidence. Oracle passed all 40 cases. NOP failed exactly every one of the 30 F2P cases and passed exactly all ten P2P cases. The hub-sequence reconciliation case is now one of those intended F2P failures. Later STB AI-credential preparation fails because reusable `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is absent; that is downstream of the current deterministic gate.

## Fresh reviewer packets

Generator run `31312573799`, artifact `9037786272`, sha256 `6f1186e2052f0bcdb9196f8418bd796c1f3598589197ce403cdc93ff2aa7d90f` generated the exact packets; the temporary workflow was removed after committing the packet bytes.

Q4 packet:
`.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.packet.json`
Result path:
`.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.json`
Role hash: `696aa3da8960a5c5ee1b093d2b8bced4e3f95fba130883ee4afc58c846251832`.

Q6 packet:
`.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.packet.json`
Result path:
`.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.json`
Role hash: `d133a8d561746bb33b8622cb3e564feccfbfe669e9e601f1d0dba95762dfb29b`.

Historical `fc137e82` and `a57ed7e6` semantic results remain retained only as stale history and cannot satisfy the current interlock.

## Current blocker / next action

Require clean packet-head Agent-System PASS. Then run Q4 and Q6 independently in separate cold contexts using the c3ee2778 packets, commit each exact result JSON to the declared result path, validate provenance, and only then evaluate `QUALITY_INTERLOCK_PASS`.

## Circuit breakers

- Status: `CLEAR`
- Attempts: `0`

## Resume rule

Require frozen task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0`, clean packet-head freshness PASS, and current c3ee2778 Q4/Q6 result validation before Quality Interlock aggregation.
