# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains `large_system_strict` with 5,530 substantive solver-visible runtime/configuration LOC, 26 mapped requirements and exactly 40 tests = 30 F2P + 10 P2P. Fourth-cycle Q4 remediation retains the natural handoff, clarifies the delegated confirmed-watermark and post-publish fencing boundaries, adds pinned live-NATS verifier dependencies, and makes the inherited hub-sequence defect behaviorally observable through the already-documented highest contiguous archive-origin progress output. No undocumented reconciliation-checksum requirement is graded.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | No hidden-test checklist expansion. |
| Q2 Verifier Coverage Repair | PASS | Eight `0fe5c749` Q4 findings repaired; suite remains exactly 30 F2P + 10 P2P and fresh matrix discriminates all 30 F2Ps. |
| Q3 Spec Ambiguity Repair | PASS | Confirmed watermark and in-flight fencing semantics are explicit in the existing delegated contract. |
| Q5 Oracle & Runtime Repair | PASS | Reference reconciliation and shared post-publish fence behavior satisfy Oracle 40/40. |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31320157239`, job `93261764319`: Preflight, Ruff, verifier build all passed. |
| Creator Complexity Gate | PASS | deterministic-head run `31320157230`; packet-head run `31320710727`; 5,530 substantive LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements. |
| Production Authenticity Gate | PASS | deterministic-head run `31320157219`; packet-head run `31320710734`. |
| Agent System / review freshness | PASS | deduplicated packet-head run `31320710733`, job `93263115624`; control-plane regressions, structure, current review freshness/commit binding and package isolation passed. |
| Preflight/static | PASS | run `31320157239`, job `93261764319`. |
| Ruff verifier | PASS | run `31320157239`, job `93261764319`. |
| Environment/verifier build | PASS | run `31320157239`, job `93261764319`; pinned NATS Server 2.14.3 and nats-py 2.15.0 verifier dependencies built successfully. |
| Oracle = 1 | PASS | run `31320157239`, job `93261764319`; 40/40 PASS. |
| NOP = 0 | PASS | run `31320157239`, job `93261764319`; reward 0 with exactly 30 F2P FAIL + 10 P2P PASS. |
| F2P/P2P empirical matrix | PASS | artifact `9039953729`, sha256 `357b913ba35e479986d5cc878141dab53e05f34c67041b49c8ba55ff04a7350a`; Oracle 40/40, NOP exactly 30/10. |
| Leakage/package checks | PASS | deduplicated packet-head Agent-System run `31320710733` passed package isolation/current review binding. |
| FROZEN_CANDIDATE | PASS | Task commit `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a`. |
| Q4 Spec-Test Contract Reviewer | PENDING_REVIEW | packet `jetstream-regional-stream-continuity-0f0947ac-spec-test-contract-b6a2908b36`. |
| Q6 Production Logic Auditor | PENDING_REVIEW | packet `jetstream-regional-stream-continuity-0f0947ac-production-logic-dae81333d9`. |
| Quality Interlock | PENDING | Requires fresh packet-bound Q4 + Q6 PASS for `0f0947...`. |
| Task Architect | PENDING | after Quality Interlock |
| Verifier Engineer | PENDING | after Quality Interlock |
| Originality & Authenticity | PENDING | after Quality Interlock |
| Difficulty design | PENDING | after Quality Interlock |
| Compliance pre-review | PENDING | after Quality Interlock |
| Instruction Reviewer | PENDING | after Quality Interlock |
| Documentation Reviewer | PENDING | after Quality Interlock |
| Comprehensive Reviewer | PENDING | after Stage-B specialists |
| Pre-LLMaJ aggregate | PENDING | after specialist and Comprehensive reviews |
| Q8 GPT Perspective Simulation | PENDING | after Pre-LLMaJ PASS |
| Q8 Claude Perspective Simulation | PENDING | after Pre-LLMaJ PASS |
| Harbor LLMaJ | PENDING | later gate; reusable AI credentials remain separate from deterministic freeze |
| GPT-5.5 difficulty ×5 | NOT_RUN | later official gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later official gate |
| Combined difficulty ×10 | NOT_RUN | later official gate |
| Per-test solvability 1/10 | NOT_RUN | later official gate |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | after all required gates |

## Fourth-cycle Q4 remediation

The current candidate repairs the `0fe5c749` Q4 BLOCKER/HIGH findings without increasing test count:

1. Confirmed convergence is tied to the generation registry `last_observed_sequence`.
2. Wrong-stream publishing is graded behaviorally without a private outcome token.
3. Reconciliation grades model-valid source ownership and payload checksum mismatches.
4. Poison quarantine requires durable `poison_events` evidence, no business dispatch, and no completed progress.
5. Same-payload P2P crosses durable effect/dispatch identity.
6. Recovery CLI P2P executes a real replay through `NatsPublisher` against isolated JetStream.
7. Replay rechecks fencing after in-flight publish before replay-state mutation.
8. Final report grading invokes real `continuityctl verify` and independently derives topology/generation/publication/archive/consumer/retention/recovery truth from config and SQLite.
9. Archived controller-log preservation is graded by SHA-256.
10. Failed effect commit cannot advance either application-effect or ack progress.
11. Hub delivery positions are proven non-authoritative by shifting only `hub_stream_sequence` values while requiring the documented highest contiguous archive-origin sequence and convergence truth to remain origin-based. The inherited starter intentionally miscomputes that exposed progress field from hub positions; the reference implementation remains origin-identity based.

Semantic remediation commit `54fbe9d73f485f5d3a944bef261146d663e32d35` initially failed Oracle collection because the verifier image lacked the production runtime's NATS dependency. Commit `0d28c545ff6b0b7afb4c1b9900bbfb9b44f8a887` added the same pinned NATS Server 2.14.3 and `nats-py==2.15.0` to the verifier image. Run `31319563943` then produced Oracle 40/40, but NOP yielded 29 F2P failures + 11 passes because the hub-sequence F2P was nondiscriminating. A competing checksum-invariance edit was rejected as a potential phantom contract requirement. Current task commit `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a` removes that checksum assertion and makes the inherited starter expose its intended hub-position/origin-progress confusion through the already-contracted `highest_contiguous_archive_origin_sequence` field. Fresh run `31320157239` proves Oracle 40/40 and NOP exactly 30 F2P failures + 10 P2P passes.

## Fresh review packets

Repository-native packet generation run `31320404144` succeeded. Artifact `9039985895` has sha256 `c9620970402c9fd1e0d6e29e25ebae0522053fe0bc318f1fffbbfacc380fd426`. Exact generated packet bytes were committed and the temporary generator was removed. A concurrently generated duplicate packet pair was deleted before reviewer invocation; the following pair is the sole authoritative current pair.

- Q4 review id: `jetstream-regional-stream-continuity-0f0947ac-spec-test-contract-b6a2908b36`
- Q4 packet: `.terminus/reviews/jetstream-regional-stream-continuity/0f0947ac/jetstream-regional-stream-continuity-0f0947ac-spec-test-contract-b6a2908b36.packet.json`
- Q4 result: `.terminus/reviews/jetstream-regional-stream-continuity/0f0947ac/jetstream-regional-stream-continuity-0f0947ac-spec-test-contract-b6a2908b36.json`
- Q6 review id: `jetstream-regional-stream-continuity-0f0947ac-production-logic-dae81333d9`
- Q6 packet: `.terminus/reviews/jetstream-regional-stream-continuity/0f0947ac/jetstream-regional-stream-continuity-0f0947ac-production-logic-dae81333d9.packet.json`
- Q6 result: `.terminus/reviews/jetstream-regional-stream-continuity/0f0947ac/jetstream-regional-stream-continuity-0f0947ac-production-logic-dae81333d9.json`

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE; Q6 PASS.
- `0fe5c749...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT; both stale.
- `0fe5c749...` artifact `9038780101`: Oracle 40/40, NOP 30/10; stale.
- `54fbe9d...` run `31319258652`, artifact `9039693749`: Oracle collection failed because verifier NATS dependencies were absent; superseded.
- `0d28c545...` run `31319563943`, artifact `9039793353`: Oracle 40/40; NOP 29 F2P FAIL + 11 PASS; superseded.
- `0f0947...` run `31320157239`, artifact `9039953729`: accepted current deterministic evidence; Oracle 40/40, NOP 30/10.

## Current blocker

Execute the sole authoritative fresh Q4 and Q6 packets independently in separate cold contexts and commit each frozen result to its packet-declared output path. Historical reviewer verdicts do not satisfy the current Quality Interlock.

## Next action

After both results are committed, validate packet/result provenance and run the machine Quality Interlock. If both current reviews are PASS with sufficient evidence and the interlock validator passes, advance to the next live Stage-B state.
