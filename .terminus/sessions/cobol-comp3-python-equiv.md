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
| Q1 Spec Gap Repair | PENDING | no current durable PASS row/evidence recorded for the strict-rebuild candidate |
| Q2 Verifier Coverage Repair | PENDING | no current durable PASS row/evidence recorded for the strict-rebuild candidate |
| Q3 Spec Ambiguity Repair | PENDING | no current durable PASS row/evidence recorded for the strict-rebuild candidate |
| Q7 Task Format Enforcer | PENDING | no current durable PASS row/evidence recorded for the strict-rebuild candidate |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | frozen final Q4: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PASS | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; deterministic closure-chain validation PASS in run `31953426334`, job `95180306897` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Protocol-2.2 scope reuse accepted by the repository validator from task commit `02a558ab...` to `bb2e042c...` because the validated production `review_scope_hash` is unchanged |
| Quality Interlock | BLOCKED | Q4 is satisfied through `ADJUDICATED_CLOSURE_PASS` and Q6 is current by scope reuse, but prospective interlock validation reports missing mandatory PASS gates Q1, Q2, Q3 and Q7 |

## Current blocker

The Protocol-2.2 Q4 circuit-breaker closure is resolved. The frozen final Q4 remains `REVISE`, but the independent Q4 Closure Adjudicator result is `PASS/HIGH/SUFFICIENT`, reconciles all five final-Q4 findings exactly once, and passes `.terminus/q4_closure.py`. No further task repair or ordinary Q4 rerun is authorized by that closure path.

Quality Interlock still cannot advance to `PRE_LLMAJ` because the current durable strict-rebuild session does not contain PASS rows for four mandatory pre-freeze quality gates: Q1 Spec Gap Repair, Q2 Verifier Coverage Repair, Q3 Spec Ambiguity Repair and Q7 Task Format Enforcer. A prospective `validate_quality_interlock.py --task cobol-comp3-python-equiv` run reported exactly these four errors and no Q4/Q6 staleness error. The same validation accepted historical Q6 reuse under the unchanged production scope.

## Required strategy change

Do not reopen Q4. Backfill the mandatory current-candidate producer-quality gates under the active Edition 3 contracts. Reuse prior evidence only when its exact currentness/provenance is demonstrable; otherwise perform fresh bounded Q1/Q2/Q3/Q7 executions. After all four rows are legitimately PASS, rerun the repository Quality Interlock validator. Only then may the controller transition to `PRE_LLMAJ`.

## Next action

Do not modify `cobol-comp3-python-equiv/**` merely because of the Q4 closure result. Establish current PASS evidence for Q1 Spec Gap Repair, Q2 Verifier Coverage Repair, Q3 Spec Ambiguity Repair and Q7 Task Format Enforcer. Then rerun `.terminus/validate_quality_interlock.py --task cobol-comp3-python-equiv`. If it passes, record Quality Interlock PASS with Q4 satisfaction `ADJUDICATED_CLOSURE_PASS` and transition to `PRE_LLMAJ`.

## Decisions that must survive chat changes

- Q4 circuit-breaker closure is complete and deterministically valid; do not start another Q4 patch loop.
- Preserve the frozen final Q4 as `REVISE`; Q4 satisfaction is the separate `ADJUDICATED_CLOSURE_PASS` route.
- Preserve the frozen Adjudicator's rejected/narrowed scopes.
- Q6 remains reusable only while its exact production-scope hash and Q6 role contract remain current; the repository validator accepted reuse for the current candidate.
- Do not fabricate Q1/Q2/Q3/Q7 PASS rows. They must be backed by legitimate current evidence.
- Quality Interlock remains BLOCKED until those four mandatory gates are PASS.
