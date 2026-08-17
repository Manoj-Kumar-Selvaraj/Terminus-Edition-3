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
| Q7 Task Format Enforcer | PASS | fresh independent no-edit Q7 at exact task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` returned `FORMAT_PASS`; complete FORMAT_GATE walk found no remaining deterministic defect; 40 pytest tests and 40/40 informative docstrings; `TASK_FILES_MODIFIED: NO` and before/after task SHA unchanged |
| Deterministic closure Oracle | PASS | current run `31965076474`, job `95208912312`: Oracle reward `1.000` on PR merge candidate containing task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` |
| Deterministic closure NOP | PASS | current run `31965076474`, job `95208912312`: NOP reward `0.000` on PR merge candidate containing task commit `3a463000607f2dcdf88785a77d2dc5767f473e05` |
| Preflight / Ruff verifier | PASS | current run `31965076474`, job `95208912312`: Preflight PASS and exact `ruff==0.12.8` verifier check PASS (`All checks passed!`) |
| Q4 Spec-Test Contract Reviewer | STALE | historical frozen final Q4 `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json`; Q4 is exact-commit and cannot be reused on `3a463000...` |
| Q4 Adjudicated Closure | STALE | historical closure `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; not current acceptance evidence |
| Q6 Production Logic Auditor | STALE | historical Q6 `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Q6 production scope changed during the earlier Q7 `task.toml`/`environment/**` repair, so Protocol scope reuse is invalid |
| Quality Interlock | BLOCKED | Q7 and current deterministic evidence are clean; fresh current-candidate Q4 and Q6 packet-bound reviews are now the first incomplete mandatory gates |

## Current blocker

Q7 is now independently complete. The final current task candidate is `3a463000607f2dcdf88785a77d2dc5767f473e05`. A fresh independent no-edit Q7 execution performed the full current FORMAT_GATE walk from the live GitHub tree and returned `STATUS: FORMAT_PASS`, with 40 module-level pytest tests, 40/40 informative test docstrings, and no task modifications.

Current deterministic evidence is also current for this exact task commit: GitHub Actions run `31965076474`, job `95208912312` passed Preflight, exact Ruff verifier checks, Oracle reward `1.000`, and NOP reward `0.000`. Artifact `9268280495` (`terminus-validation-cobol-comp3-python-equiv-31965076474-1`) is bound to head SHA `3a463000607f2dcdf88785a77d2dc5767f473e05`, digest `sha256:a0ec7a73fbd578c4707ca8d9b1065bc089dec6aa3aa0bb6e3c9f6dbd99fc6353`. The later LLMaJ credential preparation failed HTTP 401 and Harbor LLMaJ was skipped; this remains an external credential dependency and is not current Q7/deterministic task failure evidence.

The remaining Quality Interlock blockers are semantic-review freshness only: Q4 must be freshly rerun on the exact current task commit, and Q6 must be freshly rerun because its production scope changed earlier. Historical bb2e Q4/Q4-closure and historical 02a558ab Q6 remain immutable provenance but cannot satisfy the current interlock.

## Required strategy change

Freeze `3a463000607f2dcdf88785a77d2dc5767f473e05` as the current candidate and do not modify task files while current Q4/Q6 are being obtained. Generate a fresh immutable packet for `Spec-Test Contract Reviewer` using `.terminus/new_review_packet.py` semantics and a separate fresh immutable packet for `Production Logic Auditor`. Each reviewer must run in a fresh role-specific chat, remain read-only, use only packet-allowed evidence, and persist its result at the packet-declared output path.

Q4 is exact-commit-only and must bind to `3a463000607f2dcdf88785a77d2dc5767f473e05`. Q6 must bind to the same current task commit and record the current production `review_scope_hash` over `task.toml + environment/**`; do not reuse the old `e00d...` Q6 result. Q4 and Q6 must be independent of each other and must not see prior specialist verdicts before their own reviews are frozen.

If fresh Q4 returns `PASS` with sufficient evidence and fresh Q6 returns `PASS` with sufficient evidence, run the repository Quality Interlock validators. If fresh Q4 returns `REVISE`, do not silently patch: reconcile the fresh findings against the existing circuit-breaker/adjudication history under current Protocol/Q4 closure policy before authorizing any repair. If fresh Q6 returns a blocker, route it to the smallest responsible production owner.

## Next action

Generate and freeze a fresh current-candidate packet for `Q4 — Spec-Test Contract Reviewer` at task commit `3a463000607f2dcdf88785a77d2dc5767f473e05`, then route that packet to a fresh independent Q4 chat. In parallel only if packet isolation can be preserved, generate a separate fresh current-candidate packet for `Q6 — Production Logic Auditor`; otherwise run Q4 then Q6 sequentially. Do not run Quality Interlock, PRE_LLMAJ, Harbor LLMaJ, official model trials, or merge until both current semantic review prerequisites are satisfied.

## Decisions that must survive chat changes

- Current Git-derived task commit is `3a463000607f2dcdf88785a77d2dc5767f473e05`.
- Q7 is now controller `PASS` from a fresh independent no-edit `FORMAT_PASS` at that exact task SHA.
- Q7 final verification found 40 pytest tests and 40/40 informative docstrings, with no task edits.
- Current deterministic evidence: run `31965076474`, job `95208912312`, Preflight PASS, Ruff PASS, Oracle `1.000`, NOP `0.000`.
- Current deterministic artifact: ID `9268280495`, name `terminus-validation-cobol-comp3-python-equiv-31965076474-1`, digest `sha256:a0ec7a73fbd578c4707ca8d9b1065bc089dec6aa3aa0bb6e3c9f6dbd99fc6353`, bound to head SHA `3a463000...`.
- The later LLMaJ credential HTTP 401 is external infrastructure and Harbor LLMaJ was skipped; it does not invalidate current Q7/Oracle/NOP evidence.
- Q1 and Q3 remain controller PASS because solver-visible semantic surfaces are unchanged.
- Q2 remains controller PASS by the prior adjudicated disposition because executable verifier behavior is unchanged; do not reopen Q2-S01..Q2-S12 merely because test docstrings were added.
- Historical bb2e Q4 and Q4 Adjudicated Closure are stale and cannot satisfy current Quality Interlock.
- Historical Q6 is stale because production scope changed during the earlier Q7 `task.toml`/`environment/**` repair.
- The first incomplete mandatory gates are now fresh packet-bound Q4 and fresh packet-bound Q6.
- Quality Interlock remains BLOCKED until both current semantic reviews satisfy the current protocol.
