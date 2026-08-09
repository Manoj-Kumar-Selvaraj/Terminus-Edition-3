# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `<task-name>`
- Controller state: `DRAFT | PUSHED | VALIDATING | FIXING | SPEC_ALIGNMENT | FORMAT_GATE | DETERMINISTIC_VALIDATION | FROZEN_CANDIDATE | QUALITY_INTERLOCK | PRE_LLMAJ | LLMAJ | VALIDATED | DIFFICULTY_10X | RECALIBRATING | FINAL_AUDIT | SUBMISSION_READY | BLOCKED`
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
| Q1 Spec Gap Repair | PENDING | producer evidence; all graded behavior discoverable without test-dump prose |
| Q2 Verifier Coverage Repair | PENDING | producer evidence; every material solver-visible requirement meaningfully tested |
| Q3 Spec Ambiguity Repair | PENDING | producer evidence; no grading-relevant ambiguity |
| Q7 Task Format Enforcer | PENDING | exact current task/task.toml/Docker/verifier/solution/package rules |
| Creator Complexity Gate | PENDING | required for strict large-system profile |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | infrastructure dependency; not itself submission proof |
| Oracle = 1 | PENDING | Q5 owns deep repair when this/runtime fails |
| NOP = 0 | PENDING | |
| Q4 Spec-Test Contract Reviewer | PENDING | packet-bound independent quality interlock |
| Q6 Production Logic Auditor | PENDING | packet-bound independent quality interlock |
| Quality Interlock | PENDING | Q4 PASS + Q6 PASS on exact task commit |
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
| Q8 GPT Perspective Simulation | PENDING | packet-bound diagnostic; explicitly non-official model evidence |
| Q8 Claude Perspective Simulation | PENDING | packet-bound diagnostic; isolated from GPT perspective until both freeze |
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

Allowed statuses: `PASS`, `APPROVE`, `APPROVE_WITH_NOTE`, `REVISE`, `REQUEST_CHANGES`, `FAIL`, `PENDING`, `STALE`, `BLOCKED`, `NOT_RUN`, `REJECT`, `DECLINE`, `INSUFFICIENT_EVIDENCE`, `POLICY_CONFLICT`, `DIAGNOSTIC_COMPLETE`.

**Evidence rule:** semantic ready rows cite the exact current `.terminus/reviews/<task>/<commit>/<review-id>.json`; their matching packet/result provenance must validate. Deterministic ready rows cite current run/job/artifact/package evidence. Producer quality rows cite concrete artifact/change/run evidence and cannot self-certify Q4/Q6. A non-empty prose cell alone is not proof.

`SUBMISSION_READY` requires the complete mandatory gate registry in `.terminus/validate_review_freshness.py` plus the quality-interlock enforcement in `.terminus/validate_quality_interlock.py`; deleting a row cannot delete a requirement.

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
- Classification: `<ci_infrastructure | task_contract | environment | verifier | originality | template_risk | instruction_quality | documentation_quality | instruction_gap | untested_requirement | spec_ambiguity | oracle_runtime | production_logic | format_compliance | environment_gap | verifier_gap | too_easy_100_percent | test_case_0_of_10 | compliance | checklist_failure | policy_conflict | packaging | review_disagreement | insufficient_evidence | none>`
- Evidence: `<run/job/artifact/file/review ids>`

## Next action

`<single evidence-driven next action>`

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | | | | | 1.0 | | | PENDING | | |
| Q6 Production Logic Auditor | | | | | 1.0 | | | PENDING | | |
| Task Architect | | | | | | | | PENDING | | |
| Verifier Engineer | | | | | | | | PENDING | | |
| Originality | | | | | | | | PENDING | | |
| Difficulty design | | | | | | | | PENDING | | |
| Compliance pre-review | | | | | | | | PENDING | | |
| Instruction | | | | | | | | PENDING | | |
| Documentation | | | | | | | | PENDING | | |
| Comprehensive Reviewer | | | | | 1.0 | | | PENDING | | |
| Q8 GPT Perspective Simulation | | | | | 1.0 | | | PENDING | | diagnostic only |
| Q8 Claude Perspective Simulation | | | | | 1.0 | | | PENDING | | diagnostic only |
| Trial Analysis | | | | | | | | PENDING | | |
| Final Compliance | | | | | | | | PENDING | | |
| Final Human Quality | | | | | | | | PENDING | | |

A role-contract change stales only the affected role when the task is unchanged; task changes follow the impact matrix in `PROTOCOL.md`. Historical legacy reports remain historical and are not rewritten into v3.

## Quality interlock checkpoint

- Q1 spec-gap status/evidence: `<status / paths or finding IDs>`
- Q2 verifier-coverage status/evidence: `<status / paths or finding IDs>`
- Q3 ambiguity status/evidence: `<status / paths or finding IDs>`
- Q7 format status/evidence: `<status / run/path>`
- Q5 Oracle/runtime repair evidence: `<none or failure class + commit/run>`
- Q4 review ID/result: `<id / path>`
- Q4 verdict/confidence/evidence: `<verdict / confidence / sufficiency>`
- Q6 review ID/result: `<id / path>`
- Q6 verdict/confidence/evidence: `<verdict / confidence / sufficiency>`
- Quality interlock: `PASS | REVISE | PENDING | STALE | INSUFFICIENT_EVIDENCE`

Normal Pre-LLMaJ cannot start until Q4 and Q6 independently PASS with sufficient evidence and at least MEDIUM confidence on the exact task commit.

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
- Quality interlock: `<PASS / review IDs>`
- Comprehensive Reviewer: `<recommendation>`
- Checklist coverage: `<percent>`
- Adjudications: `<none or review IDs>`
- Open findings: `<finding IDs>`
- Policy conflicts: `<none or IDs>`

Harbor LLMaJ cannot run until the aggregate is PASS. Under the quality workflow, Q8's two isolated diagnostic perspectives run after aggregate PASS and before expensive model-backed evaluation.

## Q8 model-perspective simulation checkpoint

- Task commit: `<sha>`
- GPT perspective review ID/result: `<id / path>`
- GPT execution: `EXECUTED | SIMULATION_NOT_EXECUTED | PENDING`
- GPT final verifier result: `<result or not executed>`
- GPT predicted signal: `TOO_EASY | USEFUL | POSSIBLY_TOO_HARD | NOT_MEASURABLE`
- Claude perspective review ID/result: `<id / path>`
- Claude execution: `EXECUTED | SIMULATION_NOT_EXECUTED | PENDING`
- Claude final verifier result: `<result or not executed>`
- Claude predicted signal: `TOO_EASY | USEFUL | POSSIBLY_TOO_HARD | NOT_MEASURABLE`
- Cross-perspective comparison: `<only after both freeze>`

These are diagnostic simulations. Never copy them into the official GPT-5.5 ×5 or Claude Opus 4.8 ×5 evidence rows.

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
