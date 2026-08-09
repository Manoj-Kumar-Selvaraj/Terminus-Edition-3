# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `76af7499c5ec023d0db6a60ed8408e9651ad5be3`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains `large_system_strict` with 5,527 substantive solver-visible runtime/configuration LOC, 26 mapped requirements and exactly 40 tests = 30 F2P + 10 P2P. The fifth-cycle repair preserves the natural handoff and existing requirement set while strengthening the two verifier boundaries identified by the independent `0f0947` Q4 review: confirmed-generation `last_observed_sequence` is now behaviorally distinguished from journal/archive extent, and stale recovery authority is independently exercised after one replay item completes and before the next item begins. The shared replay policy now propagates stale fencing before any next-item mutation rather than writing replay state under stale authority.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | No solver-visible requirement change was needed for the `0f0947` Q4 findings. |
| Q2 Verifier Coverage Repair | PASS | Commit `1ddc6d47f8e8ecc8f42b854d65668e2c4b421e73` strengthened existing REQ-13 and REQ-20 F2P coverage without adding a test; suite remains exactly 30 F2P + 10 P2P. |
| Q3 Spec Ambiguity Repair | PASS | Existing delegated contract already specifies confirmed watermark and replay fencing semantics; Q4 found no material phantom contract or grading ambiguity. |
| Q5 Oracle & Runtime Repair | PASS | Commit `76af7499c5ec023d0db6a60ed8408e9651ad5be3` makes stale pre-item fencing stop immediately without stale replay-item mutation; fresh Oracle is 40/40. |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31323932611`, job `93271176291`: Preflight, Ruff and verifier build passed. |
| Creator Complexity Gate | PASS | run `31323932650`; 5,527 substantive LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements. |
| Production Authenticity Gate | PASS | run `31323932635`. |
| Agent System / review freshness | PENDING | Old `0f0947` packet-bound reviews are stale after task-tree repair; fresh packet pair must be generated for `76af7499...`. |
| Preflight/static | PASS | run `31323932611`, job `93271176291`. |
| Ruff verifier | PASS | run `31323932611`, job `93271176291`. |
| Environment/verifier build | PASS | run `31323932611`, job `93271176291`; pinned NATS Server 2.14.3 and nats-py 2.15.0 verifier dependencies built successfully. |
| Oracle = 1 | PASS | run `31323932611`, job `93271176291`; 40/40 PASS in 16.87s. |
| NOP = 0 | PASS | run `31323932611`, job `93271176291`; reward 0 with exactly 30 F2P FAIL + 10 P2P PASS in 16.04s. |
| F2P/P2P empirical matrix | PASS | artifact `9041006759`, sha256 `9c1a9ff9e2c53d3b75b409ebf3dccfe4cb7100092d685f86ffa0205047948398`; Oracle 40/40, NOP exactly 30/10. |
| Leakage/package checks | PENDING | Re-run Agent-System after fresh current packet binding. |
| FROZEN_CANDIDATE | PASS | Task commit `76af7499c5ec023d0db6a60ed8408e9651ad5be3`. |
| Q4 Spec-Test Contract Reviewer | PENDING_REVIEW | Fresh packet for `76af7499...` not yet generated. |
| Q6 Production Logic Auditor | PENDING_REVIEW | Fresh packet for `76af7499...` not yet generated. |
| Quality Interlock | PENDING | Requires fresh packet-bound Q4 + Q6 PASS for `76af7499...`. |
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

## Fifth-cycle Q4 remediation

The independent Q4 review bound to `0f0947acc7abeeaf0b41ca3fa5a4ae5ff9fa793a` completed `REVISE/HIGH/SUFFICIENT` with two HIGH coverage findings and no material phantom contract or grading ambiguity.

1. **REQ-13 confirmed watermark discriminator.** The existing convergence fixture made the confirmed generation `last_observed_sequence` coincide with the journal/archive high-water mark. Q2 strengthened the existing F2P so journal and archive extent stop at 5990 while the confirmed registry watermark remains 6000, proving non-convergence and required-consumer lag against the confirmed watermark; changing only the confirmed watermark to 5990 then proves convergence. The reference passes this paired behavior and the broken starter still fails it.
2. **REQ-20 between-items fencing.** Existing coverage already exercised stale entry and a lease rotation while a publish was in flight. Q2 strengthened the same F2P with a deterministic two-item replay where the lease epoch rotates after item one is durably marked `PUBLISHED` and before item two begins. The required outcome is `FencingError`, no publication of item two, item two remains `PENDING`, and the plan remains `RUNNING`.
3. **Q5 boundary repair.** The first Oracle on Q2 commit `1ddc6d47...` produced 39 PASS / 1 FAIL: the new REQ-20 boundary did not raise because shared `execute_replay_plan` caught pre-item `FencingError` and wrote `HELD`. Q5 commit `76af7499...` removes that stale-authority mutation and lets the fence error propagate before the next item.

Fresh deterministic run `31323932611` then proves Oracle 40/40 and NOP exactly 30 F2P failures + 10 P2P passes. The later reusable-AI credential step fails because reusable AI credentials are unavailable; it occurs after deterministic Oracle/NOP and is not used to claim the freeze.

## Fresh review packets

A new repository-generated packet pair is required for task commit `76af7499c5ec023d0db6a60ed8408e9651ad5be3`. Per Specialist Execution Protocol 2.1, packets must be generated by `.terminus/new_review_packet.py`; the historical `0f0947` packet pair and results cannot be reused.

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE; Q6 PASS.
- `0fe5c749...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT; stale.
- `0f0947...`: Q4 `REVISE/HIGH/SUFFICIENT` at commit `127f6bb839629e78f73d541aa744764cd2f1b5fb`; findings REQ-13 confirmed-watermark discrimination and REQ-20 between-items fencing. Q6 `PASS/HIGH/SUFFICIENT` at commit `81d36191df0b217404a9f868fe0aba1528f502a7`. Both are stale after task-tree repair.
- `1ddc6d47...` run `31323712898`, artifact `9040932931`: Q2 coverage repair; Oracle 39/40 with sole failure at new between-items fencing boundary; superseded by Q5 repair.
- `76af7499...` run `31323932611`, artifact `9041006759`: accepted current deterministic evidence; Oracle 40/40, NOP exactly 30 F2P FAIL + 10 P2P PASS.

## Current blocker

Generate and commit a fresh immutable Q4/Q6 packet pair for exact task commit `76af7499c5ec023d0db6a60ed8408e9651ad5be3`, then execute the two independent cold reviews. Historical packet-bound verdicts do not satisfy the current Quality Interlock.

## Next action

Run `.terminus/new_review_packet.py` independently for `spec-test-contract` and `production-logic`, commit the exact generated packet bytes, validate current review freshness/package isolation, then invoke Q4 and Q6 in separate fresh contexts. If both current reviews PASS with sufficient evidence and the machine Quality Interlock passes, advance to Stage-B specialists.
