# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains `large_system_strict` with 5,530 substantive solver-visible runtime/configuration LOC, 26 mapped requirements and exactly 40 tests = 30 F2P + 10 P2P. Fourth-cycle Q4 remediation retains the natural handoff, clarifies the delegated confirmed-watermark and post-publish fencing boundaries, adds the pinned live-NATS verifier dependencies, and makes the inherited hub-sequence defect behaviorally observable through the already-documented highest contiguous archive-origin progress output. No undocumented reconciliation-checksum requirement is graded.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | No hidden-test checklist expansion. |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | Eight `0fe5c749` Q4 findings repaired; suite remains 30 F2P + 10 P2P. |
| Q3 Spec Ambiguity Repair | FIX_APPLIED_PENDING_RERUN | Confirmed watermark and in-flight fencing semantics clarified in the existing delegated contract. |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | Reference reconciliation and shared post-publish fence behavior repaired. |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | Fresh Preflight/Ruff/build/package evidence required. |
| Creator Complexity Gate | PENDING_RERUN | Previous targeted runs preserved 5,530 LOC / 40 / 30+10 / 26 requirements; require clean-head rerun. |
| Production Authenticity Gate | PENDING_RERUN | Require exact current-head evidence. |
| Agent System / review freshness | PENDING_RERUN | Session rebound to task commit `0f0947...`; old reviews are historical. |
| Preflight/static | PENDING | Fresh Edition-3 run required. |
| Ruff verifier | PENDING | Fresh Edition-3 evidence required. |
| Environment/verifier build | PENDING | Fresh run required with pinned NATS Server 2.14.3 and nats-py 2.15.0. |
| Oracle = 1 | PENDING | Target 40/40 PASS. |
| NOP = 0 | PENDING | Target exactly 30 F2P FAIL + 10 P2P PASS. |
| F2P/P2P empirical matrix | PENDING | Require fresh artifact. |
| Leakage/package checks | PENDING_FRESH_EVIDENCE | Require clean-head Agent-System/package-isolation evidence. |
| FROZEN_CANDIDATE | NOT_REACHED | Older freezes are stale. |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | `0fe5c749` Q4 = REVISE/HIGH/SUFFICIENT; commit `df1821de1e2602627d2c3d526e8e1bc68d952d76`. |
| Q6 Production Logic Auditor | STALE_PASS | `0fe5c749` Q6 = PASS/HIGH/SUFFICIENT; commit `b00746103e4a7e4e4704da81e22aa68ed2afe897`; exact task binding moved. |
| Quality Interlock | PENDING | Requires deterministic refreeze and fresh packet-bound Q4 + Q6 PASS. |
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
| Harbor LLMaJ | PENDING | later gate |
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

Semantic remediation commit `54fbe9d73f485f5d3a944bef261146d663e32d35` initially failed Oracle collection because the verifier image lacked the production runtime's NATS dependency. Commit `0d28c545ff6b0b7afb4c1b9900bbfb9b44f8a887` added the same pinned NATS Server 2.14.3 and `nats-py==2.15.0` to the verifier image. Run `31319563943` then produced Oracle 40/40, but NOP yielded 29 F2P failures + 11 passes because the hub-sequence F2P was nondiscriminating after removal of the contradictory sparse-watermark fixture. A competing checksum-invariance edit was rejected as a potential phantom contract requirement. Current task commit `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a` instead removes that checksum assertion and makes the inherited starter expose its intended hub-position/origin-progress confusion through the already-contracted `highest_contiguous_archive_origin_sequence` field. All temporary writer workflows used for this correction are removed.

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE; Q6 PASS.
- `0fe5c749...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT; both stale.
- `0fe5c749...` artifact `9038780101`: Oracle 40/40, NOP 30/10; stale.
- `54fbe9d...` run `31319258652`, artifact `9039693749`: Oracle collection failed because verifier NATS dependencies were absent; superseded.
- `0d28c545...` run `31319563943`, artifact `9039793353`: Oracle 40/40; NOP 29 F2P FAIL + 11 PASS; superseded.

## Current blocker

Run the full deterministic matrix on task commit `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a`. Require clean-head Agent-System, Complexity and Production Authenticity plus Preflight/Ruff/build, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS.

## Next action

If the exact matrix passes, restore `FROZEN_CANDIDATE`, generate a new immutable Q4/Q6 packet pair bound to `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a`, remove the packet helper, verify packet-head freshness/package isolation, update PR #12 and rerun both cold reviewers independently.
