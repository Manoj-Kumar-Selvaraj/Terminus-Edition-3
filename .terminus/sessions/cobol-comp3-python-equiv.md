# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `BLOCKED`
- Working branch: `task/cobol-comp3-python-equiv-strict-rebuild`
- Pull request: `#23`
- Current task commit: `bb2e042c45873da3f3d78836d915ddb6446debf2`
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
| Q1 Spec Gap Repair | PASS | fresh independent direct Q1 execution at task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`: `STATUS=NO_GAP`, requirement completeness `SUFFICIENT`, instruction shape `PASS`, instruction/docs boundary `CLEAN`, handoff `PASS`, reverse-outline risk `LOW`; live task SHA reverified unchanged after execution |
| Q2 Verifier Coverage Repair | REPAIR_PROPOSED | fresh independent direct Q2 execution at unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`; identified partial/none/vacuous coverage and proposed Q2-S01..Q2-S12; task files were not modified. Several proposals materially overlap the frozen post-circuit-breaker Q4 boundary/closure rejected-or-latent families, so no repair is authorized before Adjudication. |
| Q3 Spec Ambiguity Repair | PENDING | held until Q2-vs-closure conflict is adjudicated |
| Q7 Task Format Enforcer | PENDING | held until Q2-vs-closure conflict is adjudicated |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | frozen final Q4: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PASS | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; deterministic closure-chain validation PASS in run `31953426334`, job `95180306897` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Protocol-2.2 scope reuse accepted by the repository validator from task commit `02a558ab...` to `bb2e042c...` because the validated production `review_scope_hash` is unchanged |
| Quality Interlock | BLOCKED | Q4 is satisfied through `ADJUDICATED_CLOSURE_PASS`, Q6 is current by scope reuse and Q1 is complete; Q2 returned `REPAIR_PROPOSED` and must be reconciled against the frozen no-drip/circuit-breaker closure before any task edit or later producer gate |

## Current blocker

The Protocol-2.2 Q4 circuit-breaker closure is resolved. The frozen final Q4 remains `REVISE`, while the independent Q4 Closure Adjudicator result is `PASS/HIGH/SUFFICIENT` and explicitly says not to reopen `REJECTED_SCOPE_REOPEN` or `LATENT_AFTER_BOUNDARY` as another ordinary task patch loop.

Q1 is complete on the unchanged final task candidate. Fresh Q2 then returned `REPAIR_PROPOSED` without modifying task files. Its proposed verifier additions include several semantic families already addressed by the frozen boundary/closure: blanket private `src.*` implementation coupling; exhaustive movement/item/warehouse policy-case expansion; additional safety/publication subclasses including duplicate effect kind/value floor/conflicting publication; stronger per-family preflight/audit demands; and corrupt archive-input verification. The Q2 result also includes other proposed coverage such as generation/date and cross-generation replay that require independent scope classification rather than an Orchestrator waiver.

Protocol 2.2 requires Adjudication when a proposed fix trades one gate against another, when reviewer/quality conclusions materially conflict, or when a latent/unchanged-scope finding appears after the no-drip boundary. The Orchestrator therefore cannot mark Q2 PASS, cannot implement Q2-S01..Q2-S12, and cannot continue to Q3 yet.

## Required strategy change

Freeze the unchanged task and route the Q2 diagnostic against the frozen `59dcf214` Adjudicator boundary plus the final `bb2e042c` Q4 Closure PASS to an independent Adjudicator. The Adjudicator must determine which Q2 proposals, if any, are legitimately controlling current blockers versus rejected-scope reopenings/latent-after-boundary learning debt. If any genuinely controlling Q2 blocker survives, strategy/policy re-entry is required before task repair because ordinary post-closure patching is not authorized. If none survives, the controller still needs an authoritative representation for satisfying the mandatory Q2 producer gate; the current Quality Interlock validator accepts only literal producer-gate `PASS` and has no adjudicated-Q2 exception.

## Next action

Do not modify `cobol-comp3-python-equiv/**`. Do not advance to Q3. Route the fresh Q2 `REPAIR_PROPOSED` result to a new independent Adjudicator together with current authoritative rules, the frozen boundary Adjudicator result `.terminus/reviews/cobol-comp3-python-equiv/59dcf214/cobol-comp3-python-equiv-59dcf214-adjudication-516e0ca6b1.json`, and the final closure result `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`. The adjudication question is whether any Q2 proposed repair remains legitimately controlling after that frozen closure boundary, and how the mandatory Q2 gate may be represented without silently waiving a semantic finding.

## Decisions that must survive chat changes

- Q4 circuit-breaker closure is complete and deterministically valid; do not start another Q4 patch loop.
- Preserve the frozen final Q4 as `REVISE`; Q4 satisfaction is the separate `ADJUDICATED_CLOSURE_PASS` route.
- Preserve the frozen Adjudicator's rejected/narrowed scopes and the closure's `REJECTED_SCOPE_REOPEN` / `LATENT_AFTER_BOUNDARY` dispositions.
- Q6 remains reusable only while its exact production-scope hash and Q6 role contract remain current; the repository validator accepted reuse for the current candidate.
- Q1 is complete: fresh direct execution returned `NO_GAP` on unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`.
- Q2 is not PASS: fresh direct execution returned `REPAIR_PROPOSED`; no task files were modified.
- Do not implement Q2 repairs or advance Q3/Q7 until the Q2-vs-closure semantic conflict is independently adjudicated.
- Quality Interlock remains BLOCKED.
