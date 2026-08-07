# Terminus Task Session

This file is the durable operational checkpoint for one Terminus task. It exists outside the task directory so it cannot accidentally enter a submission ZIP. Keep it concise and current; GitHub/CI evidence always overrides stale prose here.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | VALIDATED | DIFFICULTY_5X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY`
- Working branch: `<branch>`
- Pull request: `<number-or-none>`
- Last checkpoint commit: `<sha>`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| LLMaJ | PENDING | |
| Difficulty 5x | PENDING | |
| Per-test 1/5 minimum | PENDING | |
| Compliance audit | PENDING | |
| Human quality audit | PENDING | |
| Final package | PENDING | |

Allowed status values: `PASS`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`.

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

- Owner: `<CI Orchestrator | Task Architect | Verifier Engineer | Compliance Auditor | Difficulty Reviewer | Human Quality Reviewer | Trajectory Analyst>`
- Classification: `<ci_infrastructure | task_contract | environment | verifier | instruction_gap | environment_gap | verifier_gap | too_easy | test_case_0_of_5 | human_quality | packaging | none>`
- Evidence: `<run/job/artifact/log path>`

## Next action

`<single concrete next action>`

## Difficulty checkpoint

- Suite/model: `<model or not-run>`
- Complete-run passes: `<x/5>`
- Complete-run failures: `<x/5>`
- Verifier test cases at 0/5: `<none or names>`
- Difficulty evidence artifact: `<id/path>`
- Result freshness: `CURRENT | STALE | NOT_RUN`

Any substantive task, verifier, instruction, environment, or solution-contract change makes prior difficulty evidence `STALE` and returns the controller to `VALIDATING`.

## Decisions that must survive chat changes

- `<decision and reason>`

## Known non-task infrastructure facts

- `<for example: credential project/default STB version; never store secret values>`

## Attempts / changes

Keep only meaningful entries, newest first.

- `<timestamp or commit>` — `<change>` — `<result>`

## Do not retry blindly

- `<known dead end and why>`

## Resume rule

A new chat/controller must not trust this file alone. On resume it must read the current controller rules, current task files, current branch/PR, latest GitHub Actions run, and available artifacts. If any of those disagree with this checkpoint, update this checkpoint from the evidence before making task changes.
