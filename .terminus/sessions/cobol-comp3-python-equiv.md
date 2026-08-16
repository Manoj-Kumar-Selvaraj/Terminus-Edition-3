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
| Q2 Verifier Coverage Repair | PASS | retained adjudicated controller disposition: historical direct Q2 diagnostic remains `REPAIR_PROPOSED`, resolved by packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json`; the `3a463000...` verifier edit is docstring-only and preserves executable AST exactly after stripping test docstrings, so requirement-to-behavior coverage is unchanged. Do not reopen Q2-S01..Q2-S12. |
| Q3 Spec Ambiguity Repair | PASS | retained controller gate: fresh direct Q3 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `CLEAR`; no solver-visible specification/contract or grading behavior changed in the Q7 docstring repair |
| Q7 Task Format Enforcer | FIXED | bounded Q7 fixer at `a88d119d...` added exactly one informative first-statement docstring to each of 40 pytest test functions in `tests/test_outputs.py`; repair commit `3a463000607f2dcdf88785a77d2dc5767f473e05`, 40 additions/0 deletions, 40 tests before/after, 0/40 -> 40/40 docstrings, docstring-stripped AST equality `YES`; requires separate independent no-edit `FORMAT_PASS` |
| Deterministic closure Oracle | PASS | current run `31965076474`, job `95208912312`: Oracle reward `1.000` on PR merge candidate containing task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` |
| Deterministic closure NOP | PASS | current run `31965076474`, job `95208912312`: NOP reward `0.000` on PR merge candidate containing task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` |
| Preflight / Ruff verifier | PASS | current run `31965076474`, job `95208912312`: Preflight PASS and exact `ruff==0.12.8` verifier check PASS (`All checks passed!`) |
| Q4 Spec-Test Contract Reviewer | STALE | historical frozen final Q4 `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json`; Q4 is exact-commit and cannot be reused on `3a463000...` |
| Q4 Adjudicated Closure | STALE | historical closure `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; not current acceptance evidence |
| Q6 Production Logic Auditor | STALE | historical Q6 `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Q6 production scope already changed under prior Q7 `task.toml`/`environment/**` repair, so scope reuse remains invalid |
| Quality Interlock | BLOCKED | Q7 awaits independent no-edit `FORMAT_PASS`; Q4 and Q6 require fresh current-candidate evidence |

## Current blocker

The independent Q7 recheck at task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` found one remaining deterministic Edition 3 defect: missing informative test-function docstrings. A bounded Q7 fixer then used exact GitHub blob `79a1e9e87c46ec8bb0b3c122a1f56c04b86bd257` as its source/concurrency guard and changed only `cobol-comp3-python-equiv/tests/test_outputs.py`.

Repair commit `3a463000607f2dcdf88785a77d2dc5767f473e05` has exactly 40 additions and 0 deletions in that task file. Mechanical proof: 40 test functions before and after; 0/40 informative docstrings before and 40/40 after; ASTs are identical after stripping the inserted test-function docstrings. No verifier semantics changed.

GitHub Actions run `31965076474`, job `95208912312` is current deterministic evidence: Preflight PASS, Ruff verifier PASS, Oracle reward `1.000`, NOP reward `0.000`. The job later failed during LLMaJ credential preparation because SNORKEL authentication returned HTTP 401; Harbor LLMaJ was skipped. This remains external credential infrastructure and does not invalidate the deterministic task evidence.

The repository freshness validator on the same candidate reported the session stale only because it still named the prior task commit; it did not identify a new Q2 semantic conflict. Q1/Q2/Q3 remain controller-current because the Q7 repair changed neither solver-visible requirements nor executable verifier behavior. Historical Q4/Q4-closure and Q6 remain stale for Quality Interlock.

## Required strategy change

Do not treat the authoring Q7 fixer as acceptance evidence. Route exact task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` to a fresh independent Q7 read-only/no-edit execution. It must perform the complete current FORMAT_GATE walk and return `FORMAT_PASS` only if the package is clean, with `TASK_FILES_MODIFIED: NO`.

If Q7 passes without edits, record Q7 PASS. Preserve current deterministic evidence from run `31965076474`/job `95208912312`. Then freeze the current candidate and obtain fresh current-candidate Q4 and Q6 packet-bound reviews before Quality Interlock. Q4 must be current exact-commit. Q6 must be rerun because its production scope changed earlier. Do not reuse historical bb2e Q4 Closure PASS or historical Q6 as current acceptance evidence.

## Next action

Route task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` to a fresh independent no-edit `Q7 — Task Format Enforcer` execution. It must verify the exact task SHA, perform the full current structural/format walk including informative test docstrings, and return `STATUS: FORMAT_PASS` only if clean. It must make no task edits.

## Decisions that must survive chat changes

- Current Git-derived task commit is `3a463000607f2dcdf88785a77d2dc5767f473e05`.
- Q7 docstring repair commit is exactly `3a463000607f2dcdf88785a77d2dc5767f473e05` and changes only `tests/test_outputs.py` within the task: 40 additions, 0 deletions.
- Q7 repair proof: 40 -> 40 test functions; 0/40 -> 40/40 informative docstrings; docstring-stripped AST equality `YES`; verifier semantics unchanged.
- Q7 remains `FIXED`, not PASS, until an independent no-edit Q7 returns `FORMAT_PASS` on the current task SHA.
- Current deterministic evidence: run `31965076474`, job `95208912312`, Preflight PASS, Ruff PASS, Oracle `1.000`, NOP `0.000`; later LLMaJ credential preparation failed HTTP 401 and Harbor LLMaJ was skipped.
- Q1 and Q3 remain controller PASS because solver-visible semantic surfaces are unchanged.
- Q2 remains controller PASS by the prior adjudicated disposition because executable verifier behavior is unchanged; do not reopen Q2-S01..Q2-S12 merely because test docstrings were added.
- Historical bb2e Q4 and Q4 Adjudicated Closure are stale and cannot satisfy current Quality Interlock.
- Historical Q6 is stale because production scope changed during the earlier Q7 `task.toml`/`environment/**` repair.
- Quality Interlock remains BLOCKED until Q7 PASS plus fresh current Q4/Q6 evidence.
