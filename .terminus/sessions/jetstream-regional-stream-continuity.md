# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `BLOCKED`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `d7e131f962753acce119afba5f63bd525203d9c7`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains `large_system_strict` with 26 mapped requirements and exactly 40 tests = 30 F2P + 10 P2P. The consolidated Protocol-2.1 Q4 closure is now exact task commit `d7e131f962753acce119afba5f63bd525203d9c7`. It changes only the delegated solver-visible continuity contract and verifier tests relative to the reviewed `76af7499...` task tree: the stable report interface is documented, the three named captured incident artifacts are protected with full SHA-256 equality, the real-NATS replay P2P independently reads the expected physical west JetStream stream after `continuityctl execute-replay` and proves the expected stable replay payload identities are physically present, and redundant undocumented `ProcessingResult.status` assertions are removed while durable behavioral assertions remain. The producer-side pre-Q4 sweep completed with the 30/10 classification intact and no additional blocking Q4-class pattern found.

The first deterministic candidate `a220ee28...` produced Oracle 40/40 but NOP 31 failures + 9 passes because the strengthened P2P also asserted exact `Nats-Msg-Id == event_id`, duplicating an intentional F2P defect. That over-strong header assertion was removed at `d7e131f9...`; the P2P still crosses the real JetStream boundary and observes the physically stored stable replay payload identity. Fresh deterministic validation of `d7e131f9...` is required before refreeze.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | BLOCKED | Consolidated Q4-03 interface repair is applied at `d7e131f9...`; awaiting exact-commit deterministic validation. |
| Q2 Verifier Coverage Repair | BLOCKED | Consolidated Q4-01/Q4-02/Q4-04 verifier repairs are applied at `d7e131f9...`; awaiting exact-commit deterministic validation. |
| Q3 Spec Ambiguity Repair | BLOCKED | Stable report interface is documented in delegated `continuity-contract.md`; awaiting exact-commit deterministic validation. |
| Q5 Oracle & Runtime Repair | PENDING | Oracle must pass on `d7e131f9...`. |
| Q7 Task Format Enforcer | PENDING | Fresh Preflight/Ruff/verifier-build evidence required on `d7e131f9...`. |
| Creator Complexity Gate | PENDING | Fresh exact-task-tree result required. |
| Production Authenticity Gate | PENDING | Fresh exact-task-tree result required. |
| Agent System / package isolation | PENDING | Fresh exact-task-tree/control-head result required. |
| Preflight/static | PENDING | Fresh exact-task-tree result required. |
| Ruff verifier | PENDING | Fresh exact-task-tree result required. |
| Environment/verifier build | PENDING | Fresh exact-task-tree result required. |
| Oracle = 1 | PENDING | Must be 40/40 PASS on `d7e131f9...`. |
| NOP = 0 | PENDING | Must be exactly 30 F2P FAIL + 10 P2P PASS on `d7e131f9...`. |
| F2P/P2P empirical matrix | PENDING | Fresh validation artifact required. |
| FROZEN_CANDIDATE | BLOCKED | Do not refreeze until every required deterministic gate passes on `d7e131f9...`. |
| Q4 Spec-Test Contract Reviewer | STALE | Latest independent result is REVISE/HIGH/SUFFICIENT on historical task commit `76af7499...`; no new packet/review is authorized yet. |
| Q6 Production Logic Auditor | STALE | Latest independent result is PASS/HIGH/SUFFICIENT on historical task commit `76af7499...`; no new packet/review is authorized yet. |
| Quality Interlock | BLOCKED | No current packet-bound Q4/Q6 pair exists for `d7e131f9...`. |
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
| Harbor LLMaJ | PENDING | later gate; not authorized in this closure cycle |
| GPT-5.5 difficulty ×5 | NOT_RUN | later official gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later official gate |
| Combined difficulty ×10 | NOT_RUN | final tier |
| Per-test solvability 1/10 | NOT_RUN | later official gate |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | after all mandatory gates |

## Current Q4 closure

The independent Q4 review on exact historical task commit `76af7499c5ec023d0db6a60ed8408e9651ad5be3` was `REVISE/HIGH/SUFFICIENT` with four findings. The consolidated closure now ending at `d7e131f962753acce119afba5f63bd525203d9c7` addresses all four in one circuit-breaker cycle:

1. **Q4-01:** the real-NATS `continuityctl execute-replay` P2P derives the expected missing west replay identities before execution, independently queries the expected physical west JetStream stream afterward, decodes physically stored messages, and requires the expected stable replay `event_id` payload identities to be present. Exact message-id header retry semantics remain with the existing F2P coverage rather than making this P2P depend on an intentional baseline defect.
2. **Q4-02:** `ops/stream-state.json`, `ops/shift-handoff.txt`, and `log/archive/inc-2026-0808-17-controller.log` are each protected by full-content SHA-256 equality; mutable database/reconciliation observation state and generated `/out` reports remain outside those evidence digests.
3. **Q4-03:** `environment/continuity/docs/continuity-contract.md` defines the stable public `health.json` and `reconciliation.json` fields, types and nesting used by grading without expanding `instruction.md`.
4. **Q4-04:** the verifier no longer grades exact in-process `ProcessingResult.status` strings `COMMITTED` or `QUARANTINED`; durable effect, quarantine, dispatch, checkpoint, acknowledgement and exactly-once assertions remain.

The same closure sweep preserved the previously accepted authority distinctions: confirmed-generation watermark vs journal/archive extent; archive-origin sequence vs hub aggregate position; current vs stale same-owner epoch; completed replay item vs authority for the next item; and in-flight publish fencing. The sweep found no additional blocking Q4-class pattern before commit. This is producer-side diagnostic evidence only and does not self-certify Q4.

## Circuit breaker

Specialist Execution Protocol 2.1 circuit-breaker strategy has been followed: all current Q4 findings were consolidated and the whole verifier/solver-visible contract was swept before refreeze. The exact NOP matrix on the first candidate exposed one P2P overreach, which was corrected without weakening the required external JetStream observation. The controller remains `BLOCKED` until fresh deterministic evidence proves `d7e131f9...` is safe to refreeze.

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE; Q6 PASS.
- `0fe5c749...`: Q4 REVISE; Q6 PASS.
- `0f0947...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT.
- `76af7499...`: Q4 REVISE/HIGH/SUFFICIENT at result commit `f673ebf6bc9598a929ed814ba05925a8c97736eb`; Q6 PASS/HIGH/SUFFICIENT at result commit `b29d440fafd58127a6b635eb1d9223be5f4e6043`.
- `a220ee28...`: first consolidated closure candidate; Oracle 40/40, NOP 31 FAIL + 9 PASS, therefore not frozen.
- `d7e131f9...`: corrected consolidated closure candidate; independent semantic review not yet authorized.

## Current blocker

`BLOCKED` pending fresh deterministic validation of exact task commit `d7e131f962753acce119afba5f63bd525203d9c7`: Preflight, Ruff, verifier build, Oracle 40/40, NOP exactly 30 F2P failures + 10 P2P passes, Creator Complexity, Production Authenticity, and Agent System/package isolation must all pass.

## Next action

Run and inspect fresh deterministic CI for `d7e131f962753acce119afba5f63bd525203d9c7`. If every required result passes, update this durable session to `FROZEN_CANDIDATE`, record the exact CI evidence, then generate one fresh immutable Q4 packet and one fresh immutable Q6 packet for the same task commit using `.terminus/new_review_packet.py`. Do not run a semantic reviewer, Stage-B, or Harbor before that refreeze.
