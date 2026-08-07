# Terminus Task Session

This file is the durable operational checkpoint for one task. Keep it concise. Repository, CI and artifact evidence override stale prose here.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | PRE_LLMAJ | LLMAJ | VALIDATED | DIFFICULTY_5X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY`
- Working branch: `<branch>`
- Pull request: `<number-or-none>`
- Last checkpoint task commit: `<sha>`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| Pre-LLMaJ panel | PENDING | |
| Originality & Authenticity | PENDING | |
| Instruction Reviewer | PENDING | |
| Documentation Reviewer | PENDING | |
| Harbor LLMaJ | PENDING | |
| Difficulty 5x | PENDING | |
| Per-test 1/5 minimum | PENDING | |
| Compliance audit | PENDING | |
| Human quality audit | PENDING | |
| Final package | PENDING | |

Allowed status values: `PASS`, `REVISE`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`, `REJECT`.

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `<id>`
- Run number: `<number>`
- Job ID: `<id>`
- Commit/head SHA: `<sha>`
- Artifact ID(s): `<ids>`

## Current blocker

`<one precise blocker, or none>`

## Root-cause classification

- Owner: `<CI Orchestrator | Task Architect | Verifier Engineer | Compliance Auditor | Difficulty Reviewer | Originality Reviewer | Instruction Reviewer | Documentation Reviewer | Human Quality Reviewer | Trajectory Analyst>`
- Classification: `<ci_infrastructure | task_contract | environment | verifier | originality | template_risk | instruction_quality | documentation_quality | instruction_gap | environment_gap | verifier_gap | too_easy | test_case_0_of_5 | human_quality | packaging | none>`
- Evidence: `<run/job/artifact/file/review>`

## Next action

`<single concrete next action>`

## Pre-LLMaJ checkpoint

- Aggregate: `PASS | REVISE | PENDING | STALE`
- Task Architect: `<status>`
- Verifier Engineer: `<status>`
- Originality & Authenticity: `<status>`
- Difficulty design: `<status>`
- Compliance: `<status>`
- Instruction: `<status>`
- Documentation: `<status>`
- Open findings: `<summary>`

Harbor LLMaJ must not run until aggregate Pre-LLMaJ is PASS.

## Difficulty checkpoint

- Suite/model: `<model or not-run>`
- Complete-run passes: `<x/5>`
- Complete-run failures: `<x/5>`
- Verifier test cases at 0/5: `<none or names>`
- Difficulty evidence artifact: `<id/path>`
- Result freshness: `CURRENT | STALE | NOT_RUN`

Any substantive task, verifier, instruction, environment, or solution-contract change makes prior difficulty evidence STALE and returns the controller to normal validation.

## Writing/originality checkpoints

- Instruction verdict: `PASS | REVISE | PENDING | STALE`
- Instruction word count: `<count>`
- Documentation verdict: `PASS | REVISE | PENDING | STALE`
- Originality verdict: `PASS | REVISE | REJECT | PENDING | STALE`
- Duplicate risk: `LOW | MEDIUM | HIGH | PENDING`
- Template risk: `LOW | MEDIUM | HIGH | PENDING`
- Realism: `LOW | MEDIUM | HIGH | PENDING`

## Decisions that must survive chat changes

- `<decision and reason>`

## Known non-task infrastructure facts

- `<never store secret values>`

## Attempts / changes

- `<commit/run> — <change/finding> — <result>`

## Do not retry blindly

- `<known dead end and why>`

## Resume rule

A new controller must read `.terminus/CONTINUE_SESSION.md`, `.terminus/AGENT_SYSTEM.md`, `.terminus/reviewers/PRE_LLMAJ.md`, this checkpoint, current task files, current PR/branch, and latest Actions/artifact evidence. Correct the checkpoint first when live evidence disagrees.
