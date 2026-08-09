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
- Production-authenticity policy: `1.1`

## Current task profile

`large_system_strict`; 5,488 substantive solver-visible runtime/config LOC; 12,000 deterministic primary telemetry events; seven root-cause clusters; 26 manifestations; 28 causal edges; 11 cross-cluster pairs; 11 affected components. Current verifier: 40 tests = exactly 30 F2P + 10 P2P across 26 mapped requirements. Solver-visible production/runtime/configuration and natural `instruction.md` are unchanged by the second Q4 remediation.

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | instruction + referenced continuity contract |
| Q2 Verifier Coverage Repair | PASS | all second-cycle Q4 findings covered; exact empirical matrix current |
| Q3 Spec Ambiguity Repair | PASS | no ambiguity/phantom requirement found in latest Q4 |
| Q5 Oracle & Runtime Repair | PASS | wrong-stream positive ack reference behavior corrected |
| Q7 Task Format Enforcer | PASS | run `31312365548`, job `93242032230`: Preflight/Ruff/build PASS |
| Creator Complexity | PASS | run `31312365535`; packet-head run `31312737489` also PASS |
| Production Authenticity | PASS | run `31312365526`; packet-head run `31312737493` also PASS |
| Agent System / freshness | PASS | packet-head run `31312737488`, job `93242976476`: regression, structure, review freshness/task binding, package isolation PASS |
| Oracle | PASS | 40/40 in run `31312365548` |
| NOP | PASS | reward 0; exactly 30 F2P FAIL + 10 P2P PASS |
| F2P/P2P matrix | PASS | artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1` |
| FROZEN_CANDIDATE | PASS | task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` |
| Q4 | PENDING | `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028` |
| Q6 | PENDING | `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e` |
| Quality Interlock | PENDING | current Q4 + Q6 PASS required |
| Later gates | PENDING | Stage-B -> Comprehensive -> Pre-LLMaJ -> Q8 -> Harbor/model trials -> final gates |

## Accepted deterministic freeze evidence

Run `31312365548`, job `93242032230`, artifact `9037758650`, sha256 `8db595c300353ae133922c892294a5fb35daa4e7d9601f2d8a12d36960bfc1c1`: Oracle passes all 40 tests; NOP fails exactly every 30 F2P and passes exactly all ten P2P. Later reusable STB AI credential preparation fails because `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is absent; that is downstream of the current deterministic gate.

## Fresh reviewer packets

Generator run `31312573799`, artifact `9037786272`, sha256 `6f1186e2052f0bcdb9196f8418bd796c1f3598589197ce403cdc93ff2aa7d90f` generated the exact committed packets; the temporary generator was removed.

Q4:
- ID `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028`
- packet `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.packet.json`
- result `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028.json`
- role hash `696aa3da8960a5c5ee1b093d2b8bced4e3f95fba130883ee4afc58c846251832`

Q6:
- ID `jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e`
- packet `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.packet.json`
- result `.terminus/reviews/jetstream-regional-stream-continuity/c3ee2778/jetstream-regional-stream-continuity-c3ee2778-production-logic-f3f77e859e.json`
- role hash `d133a8d561746bb33b8622cb3e564feccfbfe669e9e601f1d0dba95762dfb29b`

Historical `fc137e82` and `a57ed7e6` Q4/Q6 results are stale history only.

## Current blocker / next action

Run Q4 and Q6 independently in separate cold contexts using the c3ee2778 packets. Commit exact result JSONs to packet-declared paths. Validate provenance and only then evaluate `QUALITY_INTERLOCK_PASS`.

## Circuit breakers

- Status: `CLEAR`
- Attempts: `0`

## Resume rule

Require frozen task commit `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` and current c3ee2778 Q4/Q6 result validation before Quality Interlock aggregation.
