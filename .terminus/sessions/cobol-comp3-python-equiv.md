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
| Q3 Spec Ambiguity Repair | PENDING | next mandatory current-candidate producer-quality gate |
| Q7 Task Format Enforcer | PENDING | run after Q3 if task SHA remains unchanged |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | frozen final Q4: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PASS | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; deterministic closure-chain validation PASS in run `31953426334`, job `95180306897` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Protocol-2.2 scope reuse accepted by the repository validator from task commit `02a558ab...` to `bb2e042c...` because the validated production `review_scope_hash` is unchanged |
| Quality Interlock | BLOCKED | Q1 and Q2 are complete; Q4 is satisfied through `ADJUDICATED_CLOSURE_PASS`; Q6 is current by scope reuse. Mandatory current-candidate gates Q3 and Q7 remain PENDING. |

## Current blocker

The Protocol-2.2 Q4 circuit-breaker closure is resolved. The frozen final Q4 remains `REVISE`, while the independent Q4 Closure Adjudicator result is `PASS/HIGH/SUFFICIENT` and no further ordinary Q4 patch loop is authorized.

Q1 is complete on the unchanged final task candidate. Q2's fresh direct diagnostic returned `REPAIR_PROPOSED` without modifying task files, so the controller routed that conflict to independent packet-bound Adjudication rather than implementing Q2-S01..Q2-S12. The canonical Adjudicator result `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json` returned `PASS/HIGH/SUFFICIENT`, `DECISION=BOTH_PARTLY`, `Q2_CONTROLLING_BLOCKER=NO`, `BOUNDED_VERIFIER_REPAIR_AUTHORIZED=NO`, and `CONTROL_PLANE_CODE_OR_POLICY_CHANGE_REQUIRED=NO`.

That adjudication classifies Q2-S04 and Q2-S06..Q2-S11 as rejected-scope-reopen-equivalent and Q2-S01, Q2-S02, Q2-S03, Q2-S05 and Q2-S12 as latent/no-drip noncontrolling observations. It explicitly authorizes the CI Orchestrator to record the Q2 producer gate as controller-owned `PASS` while preserving the frozen direct Q2 diagnostic unchanged as `REPAIR_PROPOSED`. The live Git-derived task commit remains exactly `bb2e042c45873da3f3d78836d915ddb6446debf2`; no task repair was performed.

Quality Interlock still cannot advance to `PRE_LLMAJ` because Q3 Spec Ambiguity Repair and Q7 Task Format Enforcer remain PENDING.

## Required strategy change

Do not reopen Q2 or Q4 and do not implement any Q2-S01..Q2-S12 scenario. Continue the mandatory current-candidate producer-quality sequence with a fresh bounded Q3 execution, then Q7 if Q3 completes without task changes. If either role proposes a real task change, stop and reconcile task/review staleness before continuing. If Q3 and Q7 are both legitimately PASS on the unchanged candidate, rerun `.terminus/validate_quality_interlock.py --task cobol-comp3-python-equiv` and advance only if it passes.

## Next action

Route unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2` to a fresh independent direct `Q3 — Spec Ambiguity Repairer` execution. Q3 must inspect solver-visible requirements/contracts for material ambiguity, conflicting authority, underspecified operational semantics or wording that permits multiple materially different implementations under the verifier contract. Do not expose prior Q3 conclusions or a desired PASS. Do not modify task files during the diagnostic execution. If Q3 is clean, record Q3 PASS and proceed to Q7.

## Decisions that must survive chat changes

- Q4 circuit-breaker closure is complete and deterministically valid; do not start another Q4 patch loop.
- Preserve the frozen final Q4 as `REVISE`; Q4 satisfaction is the separate `ADJUDICATED_CLOSURE_PASS` route.
- Preserve the frozen Adjudicator's rejected/narrowed scopes and the closure's `REJECTED_SCOPE_REOPEN` / `LATENT_AFTER_BOUNDARY` dispositions.
- Q6 remains reusable only while its exact production-scope hash and Q6 role contract remain current; the repository validator accepted reuse for the current candidate.
- Q1 is complete: fresh direct execution returned `NO_GAP` on unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`.
- Q2 is complete by controller disposition: preserve the direct Q2 `REPAIR_PROPOSED` diagnostic unchanged, and cite packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json` as the authority for Q2 producer-gate `PASS`. No Q2 repair is authorized.
- Do not implement Q2-S01..Q2-S12 and do not manufacture a Q2 `COVERED` result.
- Q3 and Q7 remain mandatory and PENDING.
- Quality Interlock remains BLOCKED until Q3 and Q7 are legitimately PASS.
