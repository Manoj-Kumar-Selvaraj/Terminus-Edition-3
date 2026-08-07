# Terminus Task Session

Session schema version: `2.0`

This file is the durable operational checkpoint for one task. Keep it concise. Repository, current rules, CI/artifact evidence and current reviewer policy override stale prose here.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | PRE_LLMAJ | LLMAJ | VALIDATED | DIFFICULTY_5X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY | BLOCKED`
- Working branch: `<branch>`
- Pull request: `<number-or-none>`
- Last checkpoint task commit: `<sha>`
- Agent-system policy: `2.0`
- Specialist prompt policy: `2.0`
- Pre-LLMaJ panel policy: `2.0`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| Pre-LLMaJ panel | PENDING | |
| Task Architect | PENDING | |
| Verifier Engineer | PENDING | |
| Originality & Authenticity | PENDING | |
| Difficulty design | PENDING | |
| Compliance pre-review | PENDING | |
| Instruction Reviewer | PENDING | |
| Documentation Reviewer | PENDING | |
| Harbor LLMaJ | PENDING | |
| Difficulty 5x | PENDING | |
| Per-test 1/5 minimum | PENDING | |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

Allowed status values: `PASS`, `REVISE`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`, `REJECT`, `INSUFFICIENT_EVIDENCE`.

## Latest CI

- Workflow: `<workflow>`
- Run ID: `<id>`
- Run number: `<number>`
- Job ID: `<id>`
- Commit/head SHA: `<sha>`
- Artifact ID(s): `<ids>`

## Current blocker

`<one precise blocker or none>`

## Root-cause classification

- Owner: `<role>`
- Classification: `<ci_infrastructure | task_contract | environment | verifier | originality | template_risk | instruction_quality | documentation_quality | instruction_gap | environment_gap | verifier_gap | too_easy | test_case_0_of_5 | compliance | packaging | review_disagreement | insufficient_evidence | none>`
- Evidence: `<run/job/artifact/file/review ids>`

## Next action

`<single evidence-driven next action>`

## Review evidence ledger

Keep one line per current material semantic review.

| Review | Review ID | Task commit | Policy version | Verdict | Confidence | Evidence status | Finding IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Task Architect | | | | PENDING | | | |
| Verifier Engineer | | | | PENDING | | | |
| Originality | | | | PENDING | | | |
| Difficulty design | | | | PENDING | | | |
| Compliance | | | | PENDING | | | |
| Instruction | | | | PENDING | | | |
| Documentation | | | | PENDING | | | |
| Human Quality | | | | PENDING | | | |

A PASS is current only when its task commit/input scope and policy version remain applicable.

## Pre-LLMaJ checkpoint

- Aggregate: `PASS | REVISE | REJECT | PENDING | STALE | INSUFFICIENT_EVIDENCE`
- Task commit: `<sha>`
- Panel policy: `<version>`
- Static check: `<status>`
- Adjudications: `<none or review IDs>`
- Open findings: `<finding IDs>`

Harbor LLMaJ must not run until aggregate is PASS.

## Difficulty checkpoint

- Task commit: `<sha>`
- Suite/model: `<model or not-run>`
- Complete-run passes: `<x/5>`
- Complete-run failures: `<x/5>`
- Verifier test cases at 0/5: `<none or names>`
- Difficulty evidence artifact: `<id/path>`
- Result freshness: `CURRENT | STALE | NOT_RUN`
- Trajectory review IDs: `<ids>`

Acceptance: at least two complete failures; every verifier test passes at least once; 4/5 or 5/5 complete passes is too easy; any test at 0/5 blocks.

## Writing/originality checkpoints

- Instruction verdict: `<status>`
- Instruction word count: `<count>`
- Documentation verdict: `<status>`
- Originality verdict: `<status>`
- Duplicate risk: `LOW | MEDIUM | HIGH | PENDING`
- Template risk: `LOW | MEDIUM | HIGH | PENDING`
- Realism: `LOW | MEDIUM | HIGH | PENDING`

## Adjudication ledger

| Adjudication ID | Dispute | Decision | Evidence | Recheck |
| --- | --- | --- | --- | --- |

## Circuit breakers

- Status: `CLEAR | TRIPPED`
- Trigger: `<none or exact repeated failure/finding>`
- Attempts: `<count>`
- Required strategy change/evidence: `<none or action>`

Do not repeat a tripped strategy until its dependency/evidence changes.

## Decisions that must survive chat changes

- `<decision + controlling evidence/reason>`

## Known non-task infrastructure facts

- `<never store secret values>`

## Attempts / changes

Newest first; keep only meaningful state-changing attempts.

- `<commit/run/review> — <change/finding> — <result>`

## Do not retry blindly

- `<known dead end and evidence>`

## Resume rule

A new controller must follow `.terminus/CONTINUE_SESSION.md`, load current policy files, this checkpoint, current task/PR/Actions/artifacts, reconcile review/task versions, and correct stale state before changing anything.
