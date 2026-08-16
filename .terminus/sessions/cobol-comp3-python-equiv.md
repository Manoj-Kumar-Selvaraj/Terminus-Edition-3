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
| Q1 Spec Gap Repair | PASS | retained controller gate: fresh direct Q1 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `NO_GAP`; Q7 changed only `task.toml`, `environment/Dockerfile`, `environment/.dockerignore`, and `tests/test.sh`, leaving `instruction.md` and referenced requirement contracts unchanged |
| Q2 Verifier Coverage Repair | PASS | retained controller disposition: bb2e direct Q2 diagnostic remains historical `REPAIR_PROPOSED`, resolved by packet-bound Adjudicator `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json`; Q7 did not change verifier test bodies or solver-visible requirements. Do not implement Q2-S01..Q2-S12 or rewrite the historical diagnostic. |
| Q3 Spec Ambiguity Repair | PASS | retained controller gate: fresh direct Q3 at `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `CLEAR`; Q7 did not change `instruction.md` or referenced semantic contracts |
| Q7 Task Format Enforcer | FIXED | fresh direct Q7 began at `bb2e042c45873da3f3d78836d915ddb6446debf2` and repaired four deterministic package paths, ending at `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`; requires a fresh independent no-edit `FORMAT_PASS` recheck before controller PASS because a fixer does not self-certify its own revision |
| Deterministic closure Oracle | PASS | current run `31960876405`, job `95198588781`: Oracle reward `1.000` on PR merge candidate containing task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` |
| Deterministic closure NOP | PASS | current run `31960876405`, job `95198588781`: NOP reward `0.000` on PR merge candidate containing task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` |
| Q4 Spec-Test Contract Reviewer | STALE | historical frozen final Q4 `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json`; Q4 is exact-commit and cannot be reused after the Q7 task edit |
| Q4 Adjudicated Closure | STALE | historical closure `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; live freshness validator explicitly reports bb2e closure stale versus current `a88d119d...` |
| Q6 Production Logic Auditor | STALE | historical Q6 `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; current production scope hash changed from `e00d2d343c91...` to `844ea4394e02...` after Q7 changed `task.toml` and `environment/**`, so Protocol scope reuse is invalid |
| Quality Interlock | BLOCKED | Q7 repair is not independently rechecked yet; Q4/Q4 closure and Q6 are stale on the current task commit |

## Current blocker

Q7 found and repaired deterministic Edition 3 package-format defects. The exact Q7 task diff from the prior controller checkpoint changes only:

- `cobol-comp3-python-equiv/task.toml` — tags reduced from seven to six;
- `cobol-comp3-python-equiv/environment/Dockerfile` — installs required `tmux` and `asciinema`;
- `cobol-comp3-python-equiv/environment/.dockerignore` — adds the current safe exclusion baseline while preserving the intentional solver-visible archive log;
- `cobol-comp3-python-equiv/tests/test.sh` — writes binary reward only after pytest completes.

The resulting Git-derived task commit is `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`. Current GitHub Actions run `31960876405`, job `95198588781` passed Preflight, Ruff, Docker/STB setup, Oracle reward 1 and NOP reward 0. The job then failed while preparing LLMaJ credentials with HTTP 401; that is an external credential/control-plane dependency, not a Q7 or deterministic task failure.

Protocol exact-commit/scope rules require a rewind of later semantic evidence. Repository-native `validate_review_freshness.py` on the new head explicitly reports the bb2e Q4 closure stale and Q6 stale; Q6 production scope changed from `e00d2d343c91...` to `844ea4394e02...`. The historical bb2e Q4/Q4-closure/Q6 results remain immutable learning evidence but cannot satisfy current Quality Interlock.

## Required strategy change

Do not mark Q7 PASS from the same fixer execution that authored the format repair. First route current task commit `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` to a fresh independent Q7 execution constrained to read/validate only; it must return `FORMAT_PASS` with no task edits. If it changes any task file again, repeat staleness reconciliation.

After current Q7 PASS, preserve the refreshed Oracle/NOP evidence from run `31960876405` and refreeze the current candidate. Then obtain fresh current-candidate Q4 and Q6 evidence. Q6 must be rerun because its production-scope hash changed. Q4 must be rerun because Q4 is never scope-reusable. Do not use the historical bb2e Q4 Closure PASS as current acceptance evidence; any new Q4 `REVISE` must be reconciled under the live Protocol/Q4-closure policy before Quality Interlock can advance.

## Next action

Route `a88d119d44363decb8baf6ddf4ad3b86aabd4a04` to a fresh independent direct `Q7 — Task Format Enforcer` execution. It must independently verify that exact Git-derived task SHA, perform the full current structural walk, make no edits unless a genuinely new deterministic defect exists, and return `STATUS: FORMAT_PASS` if the repaired package is now clean. Do not rerun Q4 or Q6 until Q7 is frozen clean.

## Decisions that must survive chat changes

- Current Git-derived task commit is `a88d119d44363decb8baf6ddf4ad3b86aabd4a04`, not `bb2e042c...`.
- Q7 repair changed exactly `task.toml`, `environment/Dockerfile`, `environment/.dockerignore`, and `tests/test.sh`.
- Q7 is `FIXED`, not controller PASS yet; a fresh no-edit Q7 `FORMAT_PASS` recheck is required.
- Current deterministic evidence: run `31960876405`, job `95198588781`, Preflight PASS, Ruff PASS, Oracle reward 1, NOP reward 0; later LLMaJ credential preparation failed with HTTP 401.
- Q1 and Q3 remain controller PASS because their semantic specification/ambiguity surfaces were unchanged by the Q7 format-only repair.
- Q2 remains controller PASS; verifier test bodies/requirement mapping were unchanged. Preserve the historical direct Q2 diagnostic and its historical adjudication; do not reopen Q2-S01..Q2-S12 absent genuinely changed Q2 evidence.
- Historical bb2e Q4 and Q4 Adjudicated Closure are stale for the current task commit and cannot satisfy Quality Interlock.
- Historical Q6 is stale: production scope hash changed from `e00d2d343c91...` to `844ea4394e02...`.
- Quality Interlock remains BLOCKED.
