# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `BLOCKED`
- Working branch: `task/cobol-comp3-python-equiv-strict-rebuild`
- Pull request: `#23`
- Current task commit: `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`
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
| Q1 Spec Gap Repair | PASS | retained controller gate: fresh direct Q1 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `NO_GAP`; current changes through `a88d119d...` have not changed `instruction.md` or referenced solver-visible requirement contracts |
| Q2 Verifier Coverage Repair | PASS | retained controller disposition through `a88d119d...`: bb2e direct Q2 diagnostic remains historical `REPAIR_PROPOSED`, resolved by packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json`; current Q7 changes through `a88d119d...` did not change `tests/test_outputs.py` behavioral assertions. Do not implement Q2-S01..Q2-S12 or rewrite the historical diagnostic. |
| Q3 Spec Ambiguity Repair | PASS | retained controller gate: fresh direct Q3 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `CLEAR`; current changes through `a88d119d...` have not changed `instruction.md` or referenced semantic contracts |
| Q7 Task Format Enforcer | BLOCKED | independent post-repair Q7 recheck at exact task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` found one remaining deterministic defect: every pytest test function in `tests/test_outputs.py` requires an informative docstring; no task files were modified by the recheck |
| Deterministic closure Oracle | PASS | current run `31960876405`, job `95198588781`: Oracle reward `1.000` on PR merge candidate containing task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` |
| Deterministic closure NOP | PASS | current run `31960876405`, job `95198588781`: NOP reward `0.000` on PR merge candidate containing task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` |
| Q4 Spec-Test Contract Reviewer | STALE | historical frozen final Q4 `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json`; Q4 is exact-commit and cannot be reused after the Q7 task edit |
| Q4 Adjudicated Closure | STALE | historical closure `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; live freshness validator explicitly reports bb2e closure stale versus current `a88d119d...` |
| Q6 Production Logic Auditor | STALE | historical Q6 `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; current production scope hash changed from `e00d2d343c91...` to `844ea4394e02...` after Q7 changed `task.toml` and `environment/**`, so Protocol scope reuse is invalid |
| Quality Interlock | BLOCKED | Q7 still has one deterministic format defect; Q4/Q4 closure and Q6 are stale on the current task commit |

## Current blocker

The first Q7 fixer repaired four deterministic package defects and produced task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`. Current GitHub Actions run `31960876405`, job `95198588781` passed Preflight, Ruff, Docker/STB setup, Oracle reward 1 and NOP reward 0; later LLMaJ credential preparation failed HTTP 401, which is external credential infrastructure rather than a task-format defect.

A fresh independent no-edit Q7 recheck then walked the current package from scratch and confirmed all previously repaired surfaces are clean, but found one additional settled Edition 3 requirement: every pytest test function must have an informative docstring. `cobol-comp3-python-equiv/tests/test_outputs.py` currently has test functions without docstrings. The authoritative `TERMINUS_3_AI_INSTRUCTIONS.md` explicitly requires a docstring on every test, and the FORMAT_GATE stage contract owns deterministic format defects under Q7. The recheck therefore correctly returned `STATUS: BLOCKED` and made no task edits.

Historical bb2e Q4/Q4-closure and Q6 remain stale. Q6 production scope changed from `e00d2d343c91...` to `844ea4394e02...`; they cannot support current Quality Interlock.

## Required strategy change

Route the single current FORMAT_GATE defect to a fresh Q7 fixer. The fixer may change only `cobol-comp3-python-equiv/tests/test_outputs.py`, adding concise informative docstrings to every pytest test function. It must not alter test names, decorators, fixtures, assertions, control flow, inputs, expected values, F2P/P2P classification, imports, helpers, or verifier semantics. It must verify mechanically that every test function now has a non-empty docstring and run verifier lint/static checks. Because any task edit creates a new Git-derived task commit, the controller must reconcile freshness after the fix rather than treating the fixer as acceptance evidence.

After that bounded fix, obtain a fresh independent no-edit Q7 `FORMAT_PASS` on the new task SHA. Then reconcile any verifier-change staleness before refreezing: rerun the deterministic Oracle/NOP evidence required for the new commit and obtain fresh current-candidate Q4 and Q6. Do not use historical bb2e Q4 Closure PASS or historical Q6 as current acceptance evidence.

## Next action

Route task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` to a fresh `Q7 — Task Format Enforcer` fixer execution bounded to the missing informative-test-docstring rule. It may edit only `cobol-comp3-python-equiv/tests/test_outputs.py`, add docstrings only, revalidate the docstring invariant plus verifier lint/static checks, commit the change, and return `STATUS: FIXED` with the new Git-derived task SHA. It must not self-certify `FORMAT_PASS` for its own revision.

## Decisions that must survive chat changes

- Current Git-derived task commit before the docstring repair is `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`.
- The independent Q7 recheck is `BLOCKED` solely on missing informative docstrings in `tests/test_outputs.py`; all other Q7 checks passed.
- `TERMINUS_3_AI_INSTRUCTIONS.md` explicitly requires an informative docstring on every pytest test function.
- FORMAT_GATE is owned by Q7 Task Format Enforcer; deterministic `FORMAT_DEFECT` routes back to Q7.
- The next fixer may change only `tests/test_outputs.py` and only by adding informative test-function docstrings; no verifier semantics may change.
- Q7 remains BLOCKED until a bounded fixer returns `FIXED` and a separate fresh no-edit Q7 returns `FORMAT_PASS` on the resulting task SHA.
- Current deterministic evidence at `a88d119d...`: run `31960876405`, job `95198588781`, Preflight PASS, Ruff PASS, Oracle reward 1, NOP reward 0; later LLMaJ credential preparation failed HTTP 401.
- Historical bb2e Q4 and Q4 Adjudicated Closure are stale for the current task line and cannot satisfy Quality Interlock.
- Historical Q6 is stale because its production-scope hash changed from `e00d2d343c91...` to `844ea4394e02...`.
- Quality Interlock remains BLOCKED.
