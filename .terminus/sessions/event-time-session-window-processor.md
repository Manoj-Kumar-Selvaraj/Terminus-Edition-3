# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `event-time-session-window-processor`
- Controller state: `FIXING`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `3fec54c647e703efea3e10b25d157c27f2267e81`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: d701f55d6d8c8bcde59cde211c5ae647fc45549d
CREATION_PROFILE: large_system_strict
NETWORK_MODE: public
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | `.terminus/reviews/event-time-session-window-processor/q1-spec-gap.md`; CLI modes and clean-replay discoverable |
| Q2 Verifier Coverage Repair | REPAIR_PROPOSED | VE-01..VE-05 applied on dirty tree; recheck after freeze |
| Q3 Spec Ambiguity Repair | PASS | `.terminus/reviews/event-time-session-window-processor/q3-ambiguity.md`; dropped unsupported duplicate-side-output claim |
| Q7 Task Format Enforcer | PASS | layout/Docker unchanged; README/instruction/tests only |
| Creator Complexity Gate | PASS | local validator run 1; 25 F2P / 15 P2P (count unchanged) |
| Runtime authenticity | PASS | 12000 click_event rows |
| Ruff verifier | PASS | local `ruff check` run 1; `tests/test_outputs.py` clean after repair |
| Oracle = 1 | STALE | last Harbor job `2026-08-17__13-59-38`; rerun after freeze |
| NOP = 0 | STALE | last Harbor job `2026-08-17__14-00-43`; rerun after freeze |
| Freeze | PASS | task commit `3fec54c647e703efea3e10b25d157c27f2267e81`
| Q4 Spec-Test Contract Reviewer | STALE | instruction + verifier changed; `254c526` Q4 historical |
| Q6 Production Logic Auditor | PASS | environment/task.toml unchanged; scope reuse still eligible after freeze |
| Quality Interlock | STALE | Q4 stale after producer repair |
| Pre-LLMaJ specialist panel | STALE | re-run Verifier, Instruction, Documentation, Comprehensive after freeze |
| Task Architect | STALE | instruction.md changed |
| Verifier Engineer | STALE | controlling VE-01..VE-05 repaired |
| Originality & Authenticity | PASS | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-originality-640ab5f9f7.json` |
| Difficulty design | STALE | instruction/tests changed |
| Compliance pre-review | PASS | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-compliance-a504f51368.json` |
| Instruction Reviewer | STALE | paragraph regroup applied |
| Documentation Reviewer | STALE | README §12 rewrite |
| Comprehensive Reviewer | STALE | task files changed |
| Pre-LLMaJ aggregate | REVISE | `.terminus/reviews/event-time-session-window-processor/254c5266/pre-llmaj-aggregate.md`; Adjudicator `2ac04a2a21` |
| Q8 GPT Perspective Simulation | PENDING | blocked until PRE_LLMAJ PASS |
| Q8 Claude Perspective Simulation | PENDING | blocked until PRE_LLMAJ PASS |
| Harbor LLMaJ | DEFERRED | user-deferred unless asked |
| Difficulty trials | DEFERRED | user-deferred unless asked |

## Current blocker

Producer repair applied for Adjudicator-controlling findings; task tree dirty. Next: freeze this task only, Harbor oracle/NOP, then Q4 + Verifier/Instruction/Documentation/Comprehensive re-review. Do not add task.toml explanation fields.

## Root-cause classification

- Owner: Q2 / Instruction Writer / Documentation Writer
- Classification: verifier_gap, instruction_quality, documentation_quality
- Evidence: Adjudicator `2ac04a2a21` REQUEST_CHANGES

## Next action

Harbor oracle 1 / NOP 0 on `3fec54c` with `JOBS_DIR=/tmp/e3-ets`. Then new Q4 packet (Q6 reuse if production scope hash unchanged) and cold re-reviews of Verifier, Instruction, Documentation, Comprehensive.

## Decisions that must survive chat changes

- Profile `large_system_strict`; Software/Systems; artifacts `["/app/sessions"]`.
- Planted defects unchanged.
- last_run.warehouse.event_count and ops-report.inventory.event_count equal catalog click_event COUNT(*).
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless asked.
- Leave unrelated dirty work untouched (including jetstream and cobol-comp3).
- Do not count `sql/seed.sql` or `warehouse/click_ledger.jsonl` toward Q6 LOC.
- Do not add `task.toml` `difficulty_explanation` / `solution_explanation` / `verification_explanation`.
- Do not majority-vote Comprehensive APPROVE over specialist REVISE. Adjudicator `2ac04a2a21` controls VE-01..VE-05, instruction-1, DOC-1 README-only, DOC-2. VE-06..VE-10 were not authorized.

## Quality interlock checkpoint

- Q1 spec-gap status/evidence: PASS / `.terminus/reviews/event-time-session-window-processor/q1-spec-gap.md`
- Q2 verifier-coverage status/evidence: REPAIR_PROPOSED / VE-01..VE-05 applied on dirty tree
- Q3 ambiguity status/evidence: PASS / `.terminus/reviews/event-time-session-window-processor/q3-ambiguity.md`
- Q7 format status/evidence: PASS / `.terminus/reviews/event-time-session-window-processor/q7-format-check.md`
- Q5 Oracle/runtime repair evidence: STALE; last Harbor oracle `/tmp/e3-ets/2026-08-17__13-59-38` 1.0; NOP `/tmp/e3-ets/2026-08-17__14-00-43` 0.0
- Q4 review ID/result: historical `event-time-session-window-processor-254c5266-spec-test-contract-eab4bc4e14` — STALE after instruction + verifier repair
- Q4 verdict/confidence/evidence: STALE / was PASS HIGH SUFFICIENT on `254c526`
- Q4 exhaustiveness: COMPLETE on frozen `254c526`; not current
- Q6 review ID/result: `event-time-session-window-processor-4927f2e3-production-logic-9c4c8e6384` / `.terminus/reviews/event-time-session-window-processor/4927f2e3/event-time-session-window-processor-4927f2e3-production-logic-9c4c8e6384.json`
- Q6 verdict/confidence/evidence: PASS / HIGH / SUFFICIENT (environment/task.toml unchanged; reuse eligible after freeze)
- Q6 production scope hash: `c52a4631cd7a23d97a66b566737ae50487e12cdc4988699900d4b71cd89b51da`
- Q6 scope reuse: `4927f2e3ebe00551671bb1273a91ed830f809d34` -> `254c52666b0996833623464fcbf3f72029bfdead` with identical hash
- Quality interlock: `STALE` (Q4 stale after producer repair)

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Scope hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | event-time-session-window-processor-254c5266-spec-test-contract-eab4bc4e14 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.1 | c860dfe8b8ed0a04c729e4d6a828741b206b7067a780863ec7b22ee09d02c5a0 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-spec-test-contract-eab4bc4e14.json` | PASS | HIGH | SUFFICIENT; exhaustive; advisory Q4-A01..A05 |
| Q6 Production Logic Auditor | event-time-session-window-processor-4927f2e3-production-logic-9c4c8e6384 | 4927f2e3ebe00551671bb1273a91ed830f809d34 | 2.2 | 2.2 | 1.1 | ee7d1cfd6e19fcc0e831cc75829457593d7410613c3b3fb811aef925e85a1607 | c52a4631cd7a23d97a66b566737ae50487e12cdc4988699900d4b71cd89b51da | `.terminus/reviews/event-time-session-window-processor/4927f2e3/event-time-session-window-processor-4927f2e3-production-logic-9c4c8e6384.json` | PASS | HIGH | SUFFICIENT; LOC 3122; reused onto 254c526 |
| Task Architect | event-time-session-window-processor-254c5266-task-architect-4ab9786064 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | bf62a53fc4373bd2bde48f07b37004bc001e81c14239c1e0bf907adf761d2536 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-task-architect-4ab9786064.json` | PASS | HIGH | SUFFICIENT; no findings |
| Originality & Authenticity | event-time-session-window-processor-254c5266-originality-640ab5f9f7 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | a85b7ae8248cbaba5b038db97e6207b51d4514816d092ef3038f4db82a3726b5 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-originality-640ab5f9f7.json` | PASS | HIGH | SUFFICIENT; no findings |
| Verifier Engineer | event-time-session-window-processor-254c5266-verifier-engineer-05b1a7505d | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | 16caaf27eb6f8f682e0da0f9e3f79183d2f07a84e33a6e421d8c10642a8117e4 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-verifier-engineer-05b1a7505d.json` | REVISE | HIGH | SUFFICIENT; blocking VE-01..VE-05 |
| Compliance Auditor | event-time-session-window-processor-254c5266-compliance-a504f51368 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | a4ce6195d206dc10def9ae5c14ac2d8cc89455a681478356c53bfca18a125470 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-compliance-a504f51368.json` | PASS | HIGH | SUFFICIENT; advisory COMP-1 COMP-2 |
| Difficulty Reviewer | event-time-session-window-processor-254c5266-difficulty-design-8c7e0b90a5 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | d80763afaced63972ac6b4eaa06bfc9779fd06dc42674f5d27122ddc2928c290 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-difficulty-design-8c7e0b90a5.json` | PASS | MEDIUM | SUFFICIENT; pre-trial; advisory DD-1..DD-3 |
| Engineering Documentation Reviewer | event-time-session-window-processor-254c5266-documentation-52bf3f2ac9 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | d775a45de3eca4ad26021c2d0f0e69ff819739533ffa97c013a1fda41f13d12e | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-documentation-52bf3f2ac9.json` | REVISE | HIGH | SUFFICIENT; blocking DOC-1 DOC-2 |
| Instruction Reviewer | event-time-session-window-processor-254c5266-instruction-edf7356de4 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | ce36982fb77ce80b4c8f53015d566f5bcfb3288c7408243b9a807b8856930703 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-instruction-edf7356de4.json` | REVISE | HIGH | SUFFICIENT; blocking instruction-1 |
| Comprehensive Reviewer | event-time-session-window-processor-254c5266-comprehensive-checklist-b08c18bc3b | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | 7b4f0432fc31dc69dcf55d9cd988930880cd7cb6c5f8ae95332d54ab128732ae | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-comprehensive-checklist-b08c18bc3b.json` | APPROVE | HIGH | SUFFICIENT; 100% coverage; 0 FAIL; does not control Stage E |
| Adjudicator | event-time-session-window-processor-254c5266-adjudication-2ac04a2a21 | 254c52666b0996833623464fcbf3f72029bfdead | 2.2 | 2.2 | 1.0 | 559077c47ef75f5c4bdbea023f30c1a2a26ba037ff4291534c836e5f342a0135 | n/a | `.terminus/reviews/event-time-session-window-processor/254c5266/event-time-session-window-processor-254c5266-adjudication-2ac04a2a21.json` | REQUEST_CHANGES | HIGH | SUFFICIENT; cluster 1 A VE-01..VE-05; clusters 2–4 BOTH_PARTLY |

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
