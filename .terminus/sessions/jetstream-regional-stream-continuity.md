# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `54fbe9d73f485f5d3a944bef261146d663e32d35`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains `large_system_strict`. Fourth-cycle Q4 remediation preserves the 40-test shape at exactly 30 F2P + 10 P2P across 26 mapped requirements. Solver-visible substantive runtime/configuration is 5,530 LOC. `instruction.md` was not expanded. The delegated continuity contract now makes only two previously ambiguous boundaries explicit: confirmed convergence uses the confirmed generation `last_observed_sequence`, and replay fencing is revalidated after an in-flight publish before replay-state mutation.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | Existing task handoff remains selective; no new hidden checklist was added. |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | All eight `0fe5c749` Q4 findings were addressed by strengthening existing tests; count remains 30 F2P + 10 P2P. |
| Q3 Spec Ambiguity Repair | FIX_APPLIED_PENDING_RERUN | Confirmed-watermark convergence and post-publish fencing boundaries are now explicit in the existing delegated contract. |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | Reference reconciliation targets the confirmed generation watermark; shared replay execution rechecks fencing after publish acknowledgement before replay-state mutation. |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | Require fresh Preflight/Ruff/build/package evidence for current task commit. |
| Creator Complexity Gate | PASS_STATIC | remediation helper strict validation: 5,530 LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements. Require clean-head rerun. |
| Production Authenticity Gate | PENDING_RERUN | Task runtime changed by seven substantive lines; previous Q6/authenticity evidence is stale for acceptance. |
| Agent System / review freshness | PENDING_RERUN | Session now rebound to current task commit; old review pair is historical. |
| Preflight/static | PENDING | Fresh Edition-3 run required. |
| Ruff verifier | PASS_STATIC | Remediation helper `ruff check` passed; fresh Edition-3 evidence still required. |
| Environment/verifier build | PENDING | Fresh Edition-3 run required. |
| Oracle = 1 | PENDING | Target 40/40 PASS. |
| NOP = 0 | PENDING | Target exactly 30 F2P FAIL + 10 P2P PASS. |
| F2P/P2P empirical matrix | PENDING | Require fresh current-task artifact. |
| Leakage/package checks | PENDING_FRESH_EVIDENCE | Require clean-head Agent-System/package-isolation evidence. |
| FROZEN_CANDIDATE | NOT_REACHED | `0fe5c749` freeze is stale after task changes. |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | `0fe5c749` result `REVISE/HIGH/SUFFICIENT`, commit `df1821de1e2602627d2c3d526e8e1bc68d952d76`, drove this remediation. |
| Q6 Production Logic Auditor | STALE_PASS | `0fe5c749` result `PASS/HIGH/SUFFICIENT`, commit `b00746103e4a7e4e4704da81e22aa68ed2afe897`; exact task-commit binding is stale after current changes. |
| Quality Interlock | PENDING | Requires deterministic refreeze plus fresh packet-bound Q4 and Q6 PASS. |
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
| Harbor LLMaJ | PENDING | later gate; reusable AI credentials are independent of deterministic validation |
| GPT-5.5 difficulty ×5 | NOT_RUN | later official gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later official gate |
| Combined difficulty ×10 | NOT_RUN | later official gate |
| Per-test solvability 1/10 | NOT_RUN | later official gate |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | after all required gates |

## Fourth-cycle Q4 remediation

Independent Q4 on `0fe5c749b7b1e389ef764032ce65a38676b51e8d` returned `REVISE/HIGH/SUFFICIENT` with one BLOCKER and seven HIGH findings. Current task commit `54fbe9d73f485f5d3a944bef261146d663e32d35` addresses them without increasing test count:

1. Convergence now uses the confirmed generation registry `last_observed_sequence`; the contradictory sparse-watermark fixture was removed while hub aggregate delivery positions remain irrelevant.
2. Wrong-stream publish grading no longer depends on an undocumented private publish-attempt outcome token.
3. Reconciliation metadata coverage now induces both a model-valid source-ownership mismatch and a model-valid payload checksum mismatch.
4. Poison/quarantine grading now requires the separate durable `poison_events` evidence row in addition to no completed effect/dispatch/progress.
5. The same-payload P2P crosses the durable effect/dispatch identity boundary instead of stopping at in-memory envelopes.
6. The recovery CLI P2P now starts an isolated west JetStream server, provisions the physical origin stream and requires `continuityctl execute-replay` to publish through the real `NatsPublisher` path.
7. Replay fencing is rechecked after an in-flight publish returns; a stale worker may retain publication acknowledgement evidence but cannot mutate replay-item or terminal plan state afterward.
8. Final report grading invokes the real `continuityctl verify`, independently derives topology, generation, publication, archive, consumer, retention and recovery health from config/SQLite, and compares all report dimensions.
9. The archived incident controller log is protected by a deterministic SHA-256 assertion alongside the existing stream-state and handoff evidence.
10. The existing failed-effect checkpoint test now also proves application-effect progress cannot advance before durable effect commit.

The remediation helper passed Ruff, Python compilation and strict complexity before committing. Its task diff is limited to the delegated contract, shared replay policy, reference engine, the two verifier modules and the private test-map wording. No global formatter was run. The temporary helper workflow was removed afterward.

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE; Q6 PASS.
- `0fe5c749...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT; both stale after fourth-cycle task changes.
- `0fe5c749...` deterministic artifact `9038780101`: Oracle 40/40 and NOP 30/10; stale after task changes.

## Current blocker

Run fresh deterministic validation for task commit `54fbe9d73f485f5d3a944bef261146d663e32d35`. Require clean-head Agent-System, Complexity and Production Authenticity plus Preflight/Ruff/build, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS. The live-NATS recovery P2P must pass both Oracle and NOP.

## Next action

If the full deterministic matrix passes, restore `FROZEN_CANDIDATE`, generate a new immutable Q4/Q6 packet pair bound to the current task commit, remove the packet helper, verify packet-head freshness/package isolation, then rerun both reviewers independently in cold contexts.
