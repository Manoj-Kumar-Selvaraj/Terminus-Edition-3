# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `BLOCKED`
- Working branch: `task/cobol-comp3-python-equiv-strict-rebuild`
- Pull request: `#23`
- Current task commit: `3a463000607f2dcdf88785a77d2dc5767f473e05`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

Large-system-strict warehouse inventory cutover task: legacy COBOL packed-decimal movement feed to restartable Python equivalence runtime with public CLI, durable SQLite state, replay/recovery, reconciliation/publication and operator preflight/audit/archive workflows.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | retained controller gate: fresh direct Q1 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `NO_GAP`; subsequent Q7 repairs did not change `instruction.md`, referenced solver-visible requirements, or executable verifier behavior |
| Q2 Verifier Coverage Repair | PASS | retained adjudicated controller disposition: historical direct Q2 diagnostic remains `REPAIR_PROPOSED`, resolved by packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json`; the `3a463000...` verifier edit is docstring-only and preserves executable behavior. Do not reopen Q2-S01..Q2-S12 absent a new controlling adjudication. |
| Q3 Spec Ambiguity Repair | PASS | retained controller gate from fresh direct Q3 at `bb2e042c45873da3f3d78836d915ddb6446debf2`; no solver-visible specification/contract change occurred in the final Q7 docstring repair |
| Q7 Task Format Enforcer | PASS | fresh independent no-edit Q7 at exact task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` returned `FORMAT_PASS`; 40 pytest tests, 40/40 informative docstrings, no task modifications |
| Deterministic closure Oracle | PASS | run `31965076474`, job `95208912312`: Oracle reward `1.000` at current task commit |
| Deterministic closure NOP | PASS | run `31965076474`, job `95208912312`: NOP reward `0.000` at current task commit |
| Preflight / Ruff verifier | PASS | run `31965076474`, job `95208912312`: Preflight PASS and Ruff PASS |
| Q4 Spec-Test Contract Reviewer | REVISE | fresh packet-bound exact-commit result `.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-spec-test-contract-1dec81c843.json`, result commit `f4aff813b0c426c7d0ec0111bb42b11b8e0df048`; `REVISE/HIGH/SUFFICIENT`, blockers `Q4-001..Q4-011`, second omission sweep PASS |
| Q4 historical Adjudicated Closure | STALE / HISTORICAL | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json` was PASS for `bb2e042c...` only; it is not current acceptance evidence, but remains controlling historical circuit-breaker evidence |
| Q4 current conflict Adjudication | PENDING | immutable packet `.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.packet.json`, packet commit `6fcccd6e29610e6af9d87917178176c593c6da86`; no repair is authorized before this result |
| Q6 Production Logic Auditor | STALE | historical Q6 production scope was invalidated by earlier `task.toml`/`environment/**` Q7 repair; fresh Q6 remains mandatory after current Q4 conflict is resolved |
| Quality Interlock | BLOCKED | current Q4 is REVISE and its post-circuit-breaker semantic conflict is pending Adjudicator disposition; fresh Q6 also remains missing |

## Current blocker

Fresh exact-commit Q4 at `3a463000607f2dcdf88785a77d2dc5767f473e05` is frozen `REVISE/HIGH/SUFFICIENT` with eleven blocking findings. The result is valid and persisted at commit `f4aff813b0c426c7d0ec0111bb42b11b8e0df048`.

This is not an ordinary repair queue. Protocol 2.2 requires Adjudicator routing when repeated exhaustive Q4 findings conflict with the already frozen circuit-breaker boundary or rely on evidence that was unchanged and previously reviewable. Historical boundary adjudication `.terminus/reviews/cobol-comp3-python-equiv/59dcf214/cobol-comp3-python-equiv-59dcf214-adjudication-516e0ca6b1.json` and historical Q4 Closure PASS at `bb2e042c...` explicitly rejected or narrowed several semantic families now raised again.

The fresh Q4 findings include:
- `Q4-001`: solver-visible implementation-diagnosis leakage in inherited source comments.
- `Q4-002`: broader movement/item/warehouse policy coverage demand.
- `Q4-003`: transfer weighted-value and transfer-overdraw coverage.
- `Q4-004`: cross-generation replay behavior coverage.
- `Q4-005`: duplicate-effect-kind / negative-value detailed-settlement subclasses.
- `Q4-006`: archive negative verification/integrity demands.
- `Q4-007`: preflight/audit domain proof and health-surface semantics.
- `Q4-008`: blanket non-public internal Python API coupling.
- `Q4-009`: overbroad no-generation-id-in-any-JSONL assertion.
- `Q4-010`: max_unit_cost / quantity_precision authority ambiguity.
- `Q4-011`: successful rejected-movement checkpoint/journal durability.

Several overlap explicit prior dispositions: blanket private `src.*` ABI theory was rejected; every-safety-subclass publication expansion was rejected; corrupt/missing archive-input testing was rejected; broad policy-case expansion was rejected after the narrowed public authority repair; rejected-movement durability was previously classified `LATENT_AFTER_BOUNDARY`. Other current findings rest on evidence that predates the Q7 format-only changes and therefore require no-drip classification rather than automatic repair.

## Required strategy change

Keep the task frozen at `3a463000607f2dcdf88785a77d2dc5767f473e05`. Do not modify any task file.

Dispatch exactly one fresh packet-bound **Adjudicator** using:

`.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.packet.json`

The Adjudicator must reconcile every fresh Q4 blocker against:
1. current authoritative Protocol 2.2 / prompt rules;
2. frozen boundary adjudication at `59dcf214...`;
3. frozen historical Q4 Closure result at `bb2e042c...`;
4. fresh Q4 result at `3a463000...`;
5. exact `bb2e042c..3a463000` task diff and current deterministic evidence.

It must decide which findings are controlling versus rejected scope reopens, latent reviewer omissions, surviving bound blockers, repair regressions, genuinely new evidence, or authoritative-rule conflicts. It must not repair task files or rerun Q4.

Only after the canonical Adjudicator result is frozen may the CI Orchestrator authorize a bounded producer/fixer scope, record a no-repair disposition, or choose a strategy redesign. Do not route Q2/Q3/Q5/Q7 fixes directly from the fresh Q4 report.

## Next action

Run the fresh Adjudicator in a separate role-specific chat with packet:

`.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.packet.json`

Expected result path:

`.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.json`

Return the frozen result to the CI Orchestrator. Do not run Q6, Quality Interlock, Pre-LLMaJ, Harbor LLMaJ, official model trials, or merge while this semantic conflict is unresolved.

## Decisions that must survive chat changes

- Current Git-derived task commit remains `3a463000607f2dcdf88785a77d2dc5767f473e05`.
- Fresh Q7 is PASS at that exact task commit.
- Current deterministic run `31965076474`, job `95208912312` has Preflight PASS, Ruff PASS, Oracle `1.000`, NOP `0.000`.
- Fresh Q4 is frozen `REVISE/HIGH/SUFFICIENT`, result commit `f4aff813b0c426c7d0ec0111bb42b11b8e0df048`, with blockers `Q4-001..Q4-011`.
- Fresh Q4 second adversarial omission sweep is PASS.
- Historical `bb2e042c` Q4 Closure PASS is stale for acceptance but remains material circuit-breaker/adjudication evidence.
- No task repair is authorized from the fresh Q4 report before current conflict adjudication.
- Current Adjudicator packet is `.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.packet.json`, frozen in commit `6fcccd6e29610e6af9d87917178176c593c6da86`.
- Q6 remains stale and mandatory, but is deferred until the Q4 conflict is resolved.
- Quality Interlock remains BLOCKED.
- PR #23 remains draft/open and must not be merged.
