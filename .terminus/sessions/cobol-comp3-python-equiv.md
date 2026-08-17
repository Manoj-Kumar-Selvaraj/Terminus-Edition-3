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

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | retained controller disposition from `bb2e042c...`; no solver-visible requirement change since then |
| Q2 Verifier Coverage Repair | PASS / ABOUT TO BE STALE | current `3a463000...` executable verifier behavior is still the adjudicated bb2e behavior, but the authorized closure cycle now requires a new Q2-owned verifier repair before refreeze |
| Q3 Spec Ambiguity Repair | PASS | no solver-visible specification/contract change at current task commit |
| Q7 Task Format Enforcer | PASS | fresh independent no-edit `FORMAT_PASS` at `3a463000607f2dcdf88785a77d2dc5767f473e05`; 40 tests, 40/40 informative docstrings |
| Preflight / Ruff | PASS | run `31965076474`, job `95208912312` |
| Oracle | PASS | run `31965076474`, job `95208912312`, reward `1.000` |
| NOP | PASS | run `31965076474`, job `95208912312`, reward `0.000` |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-spec-test-contract-1dec81c843.json`, commit `f4aff813b0c426c7d0ec0111bb42b11b8e0df048`, HIGH/SUFFICIENT |
| Current Q4 conflict Adjudication | REQUEST_CHANGES / COMPLETE | `.terminus/reviews/cobol-comp3-python-equiv/3a463000/cobol-comp3-python-equiv-3a463000-adjudication-b9b9c6b101.json`, commit `686eee0d30ececc770d30a018c6bfe806b0a58b8`, BOTH_PARTLY, HIGH/SUFFICIENT |
| Q6 Production Logic Auditor | STALE | earlier Q7 `task.toml`/`environment/**` repair invalidated historical Q6; fresh Q6 required after closure repair/refreeze |
| Quality Interlock | BLOCKED | six adjudicated Q4 semantic families require one bounded non-blind repair cycle; Q6 also missing |

## Controlling adjudication

The current Adjudicator upheld exactly six semantic families and rejected the other fresh-Q4 expansions. No finding was classified as genuinely new evidence, Q7 repair regression, or authoritative-rule conflict.

Controlling repair families:

1. `Q4-001` — solver-visible defect-diagnostic comments: comments-only neutralization in exactly six `environment/equiv/src/*.py` files; no executable behavior change.
2. `Q4-003` — verifier proof for transfer absolute source-weighted valuation and transfer overdraw.
3. `Q4-004` — verifier processing-path proof that the same movement identity is independently valid across distinct generation identities while same-generation replay remains suppressed.
4. `Q4-007` preflight portion only — discriminating batch-window and authorization/safety public-state/input probes; no audit output-shape expansion.
5. `Q4-009` — narrow the global no-generation-id-in-any-JSONL assertion to publication/publication-success evidence while preserving no-publication semantics.
6. `Q4-011` — verifier proof of successful rejected-movement journal/checkpoint durability and processed state where applicable.

Rejected/noncontrolling families that must not be reopened in this repair cycle:

- `Q4-002` broad per-policy-case coverage expansion.
- `Q4-005` every detailed-settlement/safety subclass publication expansion.
- `Q4-006` corrupt/missing archive-input expansion.
- `Q4-007` stronger audit output-shape/accounting-field expansion.
- `Q4-008` blanket private `src.*` ABI theory.
- `Q4-010` broader max-unit-cost/quantity-precision authority expansion.

## Authorized repair boundary

Exactly one consolidated non-blind repair/refreeze cycle is authorized. Because the authorized paths cross producer ownership, execute it as two role-specific producer steps within the same controller repair cycle:

### Step A — A2 Environment Builder

Allowed task paths only:

- `cobol-comp3-python-equiv/environment/equiv/src/policy.py`
- `cobol-comp3-python-equiv/environment/equiv/src/generation.py`
- `cobol-comp3-python-equiv/environment/equiv/src/checkpoint.py`
- `cobol-comp3-python-equiv/environment/equiv/src/pipeline.py`
- `cobol-comp3-python-equiv/environment/equiv/src/reconciliation.py`
- `cobol-comp3-python-equiv/environment/equiv/src/publication.py`

Allowed mutation: rewrite only defect-diagnostic comments into neutral invariant/interface/readability comments. No executable token/AST/control-flow/literal/import/signature/behavior change.

### Step B — Q2 Verifier Coverage Repairer

Run only after Step A is verified. Allowed task path only:

- `cobol-comp3-python-equiv/tests/test_outputs.py`

Allowed semantic changes only for Q4-003, Q4-004, preflight-only Q4-007, Q4-009 and Q4-011 as described above. Preserve all rejected/noncontrolling boundaries. Do not change instruction/contracts/environment/solution/schema.

This is one controller-authorized closure cycle even though two artifact owners execute sequentially. Neither producer may self-certify the final candidate.

## Staleness after the repair cycle

Any Step A environment change makes Q6 stale/current-scope-changed and also stales Q4, Q7, Oracle/NOP and other environment-sensitive gates. Step B verifier change also stales Q4, Q7, Oracle/NOP and verifier/spec-alignment evidence. Do not run expensive semantic/model gates between Step A and Step B. Refreeze only after both authorized producer steps complete and their diffs are verified.

After both steps:

1. verify exact combined task diff is within adjudicated scope;
2. rerun deterministic Preflight/Ruff/Oracle/NOP on the new exact task commit;
3. rerun fresh independent no-edit Q7 on the final combined repair commit;
4. reconcile producer-side Q1/Q2/Q3 freshness under current rules;
5. run exactly one fresh exact-commit exhaustive Q4; if any same controlling semantic blocker survives, remain BLOCKED and require strategy redesign/new adjudication rather than another ordinary repair loop;
6. run fresh Q6 on the new production-scope hash;
7. only then attempt Quality Interlock / PRE_LLMAJ.

## Current next action

Route Step A only: fresh A2 Environment Builder bounded comments-only repair starting from exact task commit `3a463000607f2dcdf88785a77d2dc5767f473e05`. Do not start Q2 until the A2 commit/diff is independently verified by the CI Orchestrator.

## Decisions that must survive chat changes

- Current Git-derived task commit before closure repair is `3a463000607f2dcdf88785a77d2dc5767f473e05`.
- Current adjudication result commit is `686eee0d30ececc770d30a018c6bfe806b0a58b8`.
- Repair is authorized: YES, but only within the six controlling semantic families and only for the exact paths described above.
- The repair cycle is split by artifact ownership: A2 comments-only first, Q2 verifier-only second.
- No instruction.md, runtime-contract.md, schema, solution behavior, or production executable-logic change is authorized.
- No repair is authorized for Q4-002/Q4-005/Q4-006/Q4-008/Q4-010 or the audit-output-shape portion of Q4-007.
- PR #23 remains draft/open and must not be merged.
