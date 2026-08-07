# Terminus Task Session

Session schema version: `2.2`

This file is the durable operational checkpoint for one task. Keep it concise. Repository, current rules, CI/artifact evidence and current reviewer policy override stale prose here.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | PRE_LLMAJ | LLMAJ | VALIDATED | DIFFICULTY_10X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY | BLOCKED`
- Working branch: `<branch>`
- Pull request: `<number-or-none>`
- Current task commit: `<sha>`
- Agent-system policy: `2.1`
- Specialist prompt policy: `2.1`
- Pre-LLMaJ panel policy: `2.1`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| Pre-LLMaJ specialist panel | PENDING | |
| Task Architect | PENDING | |
| Verifier Engineer | PENDING | |
| Originality & Authenticity | PENDING | |
| Difficulty design | PENDING | |
| Compliance pre-review | PENDING | |
| Instruction Reviewer | PENDING | |
| Documentation Reviewer | PENDING | |
| Comprehensive Reviewer | PENDING | checklist coverage must be 100% |
| Pre-LLMaJ aggregate | PENDING | |
| Harbor LLMaJ | PENDING | |
| GPT-5.5 difficulty ×5 | PENDING | diagnostic half of final trial set |
| Claude Opus 4.8 difficulty ×5 | PENDING | diagnostic half of final trial set |
| Combined difficulty ×10 | PENDING | final tier decision |
| Per-test solvability 1/10 | PENDING | every individual verifier case must pass at least once across combined 10 |
| Trial Analysis | PENDING | |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

Allowed status values: `PASS`, `APPROVE`, `APPROVE_WITH_NOTE`, `REVISE`, `REQUEST_CHANGES`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`, `REJECT`, `DECLINE`, `INSUFFICIENT_EVIDENCE`, `POLICY_CONFLICT`.

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
- Classification: `<ci_infrastructure | task_contract | environment | verifier | originality | template_risk | instruction_quality | documentation_quality | instruction_gap | environment_gap | verifier_gap | too_easy_100_percent | test_case_0_of_10 | compliance | checklist_failure | policy_conflict | packaging | review_disagreement | insufficient_evidence | none>`
- Evidence: `<run/job/artifact/file/review ids>`

## Next action

`<single evidence-driven next action>`

## Review evidence ledger

| Review | Review ID | Task commit | Policy version | Verdict | Confidence | Evidence status | Finding IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Task Architect | | | | PENDING | | | |
| Verifier Engineer | | | | PENDING | | | |
| Originality | | | | PENDING | | | |
| Difficulty design | | | | PENDING | | | |
| Compliance | | | | PENDING | | | |
| Instruction | | | | PENDING | | | |
| Documentation | | | | PENDING | | | |
| Comprehensive Reviewer | | | 1.0 | PENDING | | | |
| Human Quality | | | | PENDING | | | |

A PASS/APPROVE is current only when its task/input scope and the role-specific policy change scope remain applicable. A policy update does not automatically stale unrelated roles if their decision contract/evidence rules did not change.

## Comprehensive reviewer checkpoint

- Review ID: `<id>`
- Task commit: `<sha>`
- Reviewer policy: `1.0`
- Checklist snapshot: `2026-08-08-user-supplied`
- Policy freshness: `CURRENT | UNVERIFIED | STALE`
- Checklist total: `<count>`
- Checklist coverage: `<percent>`
- Recommendation: `APPROVE | APPROVE_WITH_NOTE | REQUEST_CHANGES | DECLINE | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT`
- High failures: `<count>`
- Medium failures: `<count>`
- Low failures: `<count>`
- Special trial revision flags: `<none or IDs>`
- Test-quality eval dispositions: `<review/report reference>`
- Trial-analysis dispositions: `<review/report reference>`
- Policy conflicts: `<none or IDs>`

`CHECKLIST_COVERAGE` must be 100% for the Comprehensive Reviewer to count as complete.

## Pre-LLMaJ checkpoint

- Aggregate: `PASS | REVISE | REJECT | PENDING | STALE | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT`
- Task commit: `<sha>`
- Panel policy: `2.1`
- Static check: `<status>`
- Comprehensive Reviewer: `<recommendation>`
- Checklist coverage: `<percent>`
- Adjudications: `<none or review IDs>`
- Open findings: `<finding IDs>`
- Policy conflicts: `<none or IDs>`

Harbor LLMaJ must not run until aggregate is PASS.

## Difficulty / solvability checkpoint

- Task commit: `<sha>`
- GPT-5.5 trials completed: `<0-5>`
- GPT complete passes: `<0-5>`
- Claude Opus 4.8 trials completed: `<0-5>`
- Claude complete passes: `<0-5>`
- Combined trials completed: `<0-10>`
- Combined complete passes: `<0-10>`
- Combined complete pass rate: `<percent>`
- Measured tier: `FRONTIER | ADVANCED | CORE | BASE | TOO_EASY_REJECT | NOT_MEASURED`
- Verifier test cases at 0/10: `<none or names>`
- Difficulty evidence artifact(s): `<ids/paths>`
- Result freshness: `CURRENT | STALE | NOT_RUN`
- Trajectory review IDs: `<ids>`
- Solvability policy: `each individual verifier test passes at least once across the combined 10 official trials`

Tier mapping: `<20% frontier`, `20–<50 advanced`, `50–<80 core`, `80–<100 base`, `100% reject`. A five-run model suite is diagnostic only and cannot set the final tier or 1/10 solvability result by itself.

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

## Policy-conflict ledger

| Conflict ID | Source A | Source B | Impact | Resolution/status |
| --- | --- | --- | --- | --- |

Never silently resolve an acceptance-relevant conflict between the stored reviewer checklist and current authoritative Edition 3 validators/rules.

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

A new controller must follow `.terminus/CONTINUE_SESSION.md`, load the current reviewer checklist and criterion registry, current policy files, this checkpoint, current task/PR/Actions/artifacts, reconcile review/task versions and policy conflicts, and correct stale state before changing anything.
