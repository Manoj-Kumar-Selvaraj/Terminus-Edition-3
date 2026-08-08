# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | PRE_LLMAJ | LLMAJ | VALIDATED | DIFFICULTY_10X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY | BLOCKED`
- Working branch: `<branch>`
- Pull request: `<number-or-none>`
- Current task commit: `<git-derived-sha>`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PENDING | required for strict large-system profile |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | infrastructure dependency; not itself submission proof |
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
| Difficulty trials | PENDING | GPT-5.5 ×5 plus Claude Opus 4.8 ×5 |
| GPT-5.5 difficulty ×5 | PENDING | diagnostic half |
| Claude Opus 4.8 difficulty ×5 | PENDING | diagnostic half |
| Combined difficulty ×10 | PENDING | final tier |
| Per-test solvability 1/10 | PENDING | every verifier case passes at least once across combined 10 |
| Trial Analysis | PENDING | packet-bound Trajectory Analyst review |
| Final Compliance | PENDING | packet-bound Compliance Auditor review |
| Final Human Quality | PENDING | packet-bound Human Quality Reviewer review |
| Final package | PENDING | |

Allowed statuses: `PASS`, `APPROVE`, `APPROVE_WITH_NOTE`, `REVISE`, `REQUEST_CHANGES`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`, `REJECT`, `DECLINE`, `INSUFFICIENT_EVIDENCE`, `POLICY_CONFLICT`.

**Evidence rule:** semantic ready rows cite the exact current `.terminus/reviews/<task>/<commit>/<review-id>.json`; their matching packet/result provenance must validate. Deterministic ready rows cite current run/job/artifact/package evidence. A non-empty prose cell alone is not proof.

`SUBMISSION_READY` requires the complete mandatory gate registry in `.terminus/validate_review_freshness.py`; deleting a row cannot delete a requirement.

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

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Task Architect | | | | | | | | PENDING | | |
| Verifier Engineer | | | | | | | | PENDING | | |
| Originality | | | | | | | | PENDING | | |
| Difficulty design | | | | | | | | PENDING | | |
| Compliance pre-review | | | | | | | | PENDING | | |
| Instruction | | | | | | | | PENDING | | |
| Documentation | | | | | | | | PENDING | | |
| Comprehensive Reviewer | | | | | 1.0 | | | PENDING | | |
| Trial Analysis | | | | | | | | PENDING | | |
| Final Compliance | | | | | | | | PENDING | | |
| Final Human Quality | | | | | | | | PENDING | | |

A role-contract change stales only the affected role when the task is unchanged; task changes follow the impact matrix in `PROTOCOL.md`. Historical legacy reports remain historical and are not rewritten into v3.

## Comprehensive reviewer checkpoint

- Review ID: `<id>`
- Result path: `<path>`
- Task commit: `<sha>`
- Role contract hash: `<hash>`
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

`CHECKLIST_COVERAGE` must be 100% for an APPROVE/APPROVE_WITH_NOTE to support a ready gate.

## Pre-LLMaJ checkpoint

- Aggregate: `PASS | REVISE | REJECT | PENDING | STALE | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT`
- Aggregate path: `<path>`
- Task commit: `<sha>`
- Panel policy: `2.2`
- Static check: `<status>`
- Comprehensive Reviewer: `<recommendation>`
- Checklist coverage: `<percent>`
- Adjudications: `<none or review IDs>`
- Open findings: `<finding IDs>`
- Policy conflicts: `<none or IDs>`

Harbor LLMaJ cannot run until the aggregate is PASS.

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
- Verifier cases at 0/10: `<none or names>`
- Difficulty artifact(s): `<ids/paths>`
- Result freshness: `CURRENT | STALE | NOT_RUN`
- Trajectory review IDs/paths: `<ids/paths>`
- Solvability policy: `every individual verifier case passes at least once across the combined 10 official trials`

Tier mapping: `<20% frontier`, `20–<50 advanced`, `50–<80 core`, `80–<100 base`, `100% reject`. A five-run suite is diagnostic only.

## Adjudication ledger

| Adjudication ID | Dispute | Decision | Evidence | Recheck |
| --- | --- | --- | --- | --- |

## Policy-conflict ledger

| Conflict ID | Source A | Source B | Impact | Resolution/status |
| --- | --- | --- | --- | --- |

Never silently resolve an acceptance-relevant current-rule conflict. The combined-ten difficulty rule is already resolved and is not itself a conflict.

## Circuit breakers

- Status: `CLEAR | TRIPPED`
- Trigger: `<none or exact repeated failure/finding>`
- Attempts: `<count>`
- Required strategy change/evidence: `<none or action>`

## Decisions that must survive chat changes

- `<decision + controlling evidence/reason>`

## Known non-task infrastructure facts

- `<never store secret values>`

## Attempts / changes

Newest first; keep only meaningful state-changing attempts.

- `<commit/run/review> — <change/finding> — <result>`

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
