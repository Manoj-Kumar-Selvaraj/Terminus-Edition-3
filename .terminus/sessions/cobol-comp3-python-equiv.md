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
| Q2 Verifier Coverage Repair | PASS | controller disposition from packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json` (`PASS/HIGH/SUFFICIENT`, `Q2_CONTROLLING_BLOCKER=NO`, no bounded verifier repair authorized). Preserve frozen direct Q2 diagnostic `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q2-verifier-coverage-direct-20260816.md` as `REPAIR_PROPOSED`; do not rewrite it to `COVERED`. |
| Q3 Spec Ambiguity Repair | PASS | fresh independent direct Q3 execution at unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`: `STATUS=CLEAR`, no ambiguities, implementation freedom preserved, instruction-policy compliance `PASS`, spec-file-loophole risk `LOW`, spec-dump risk `LOW`; task files were not modified and live task SHA was reverified unchanged |
| Q7 Task Format Enforcer | PENDING | final mandatory current-candidate producer-quality gate before Quality Interlock rerun |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | frozen final Q4: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PASS | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; deterministic closure-chain validation PASS in run `31953426334`, job `95180306897` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Protocol-2.2 scope reuse accepted by the repository validator from task commit `02a558ab...` to `bb2e042c...` because the validated production `review_scope_hash` is unchanged |
| Quality Interlock | BLOCKED | Q1/Q2/Q3 are complete; Q4 is satisfied through `ADJUDICATED_CLOSURE_PASS`; Q6 is current by scope reuse. Q7 remains the sole missing mandatory producer-quality PASS gate. |

## Current blocker

The Protocol-2.2 Q4 circuit-breaker closure is resolved. The frozen final Q4 remains `REVISE`, while the independent Q4 Closure Adjudicator result is `PASS/HIGH/SUFFICIENT` and no further ordinary Q4 patch loop is authorized.

Q1 is complete on the unchanged final task candidate. Q2 is complete by controller disposition after packet-bound Adjudication established that none of the frozen direct Q2 `REPAIR_PROPOSED` scenarios is a controlling current blocker and no verifier repair is authorized. Q3 has now completed independently on the same unchanged task commit with `STATUS=CLEAR`, no material ambiguity, preserved implementation freedom, instruction-policy compliance `PASS`, and no task-file edits.

The live Git-derived task commit remains exactly `bb2e042c45873da3f3d78836d915ddb6446debf2`, so Q3 did not stale Q4 closure, Q6 scope reuse, Oracle/NOP evidence, or the earlier producer-gate dispositions.

Quality Interlock still cannot advance to `PRE_LLMAJ` because Q7 Task Format Enforcer remains PENDING.

## Required strategy change

Do not reopen Q2, Q3 or Q4. Continue with one fresh bounded Q7 Task Format Enforcer execution on the unchanged candidate. If Q7 proposes a real task change, stop and reconcile all affected staleness before continuing. If Q7 passes without task changes, record Q7 PASS and rerun `.terminus/validate_quality_interlock.py --task cobol-comp3-python-equiv`. Advance only if the repository validator passes.

## Next action

Route unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2` to a fresh independent direct `Q7 — Task Format Enforcer` execution under the current authoritative Edition 3 structural contract and enforcement code/CI. Do not expose a desired PASS and do not modify task files during the diagnostic execution. If Q7 is clean, record Q7 PASS and immediately run the Quality Interlock validator.

## Decisions that must survive chat changes

- Q4 circuit-breaker closure is complete and deterministically valid; do not start another Q4 patch loop.
- Preserve the frozen final Q4 as `REVISE`; Q4 satisfaction is the separate `ADJUDICATED_CLOSURE_PASS` route.
- Preserve the frozen Adjudicator's rejected/narrowed scopes and the closure's `REJECTED_SCOPE_REOPEN` / `LATENT_AFTER_BOUNDARY` dispositions.
- Q6 remains reusable only while its exact production-scope hash and Q6 role contract remain current; the repository validator accepted reuse for the current candidate.
- Q1 is complete: fresh direct execution returned `NO_GAP` on unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`.
- Q2 is complete by controller disposition: preserve the direct Q2 `REPAIR_PROPOSED` diagnostic unchanged, and cite packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json` as the authority for Q2 producer-gate `PASS`. No Q2 repair is authorized.
- Q3 is complete: fresh direct execution returned `CLEAR` on unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`; no ambiguity repair or task edit was required.
- Q7 is the only remaining mandatory producer-quality gate.
- Quality Interlock remains BLOCKED until Q7 is legitimately PASS and the deterministic validator passes.
