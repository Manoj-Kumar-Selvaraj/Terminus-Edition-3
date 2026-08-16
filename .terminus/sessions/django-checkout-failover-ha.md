# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `django-checkout-failover-ha`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `582e0209de4595e14aecff692376800f209a610b`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | not re-verified after controller reconcile |
| Q2 Verifier Coverage Repair | PENDING | 30 F2P + 6 P2P present; coverage not re-certified |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | layout present; `tests/test_ha.py` not `test_outputs.py`; no CTRF flag |
| Creator Complexity Gate | PASS | `validate_task_complexity.py` PASS (still seed-inflated total); reachable Python non-blank LOC excl. `generate_seed.py` = 3011 |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PASS | Harbor job `jobs/2026-08-16__15-47-37` trial `django-checkout-failover-ha__D7WQKxP` reward.txt=`1`; 36/36 pytest |
| NOP = 0 | PASS | Harbor job `jobs/2026-08-16__15-49-48` trial `django-checkout-failover-ha__JcrgyQf` reward.txt=`0`; many F2P fail on starter |
| Q4 Spec-Test Contract Reviewer | PENDING | blocked until task commit is recorded and packets generated |
| Q6 Production Logic Auditor | PENDING | blocked until task commit is recorded and packets generated |
| Quality Interlock | PENDING | |
| Pre-LLMaJ specialist panel | PENDING | |
| Task Architect | PENDING | |
| Verifier Engineer | PENDING | |
| Originality & Authenticity | REVISE | prior house-shell finding; destemplate applied; scale authenticity still open |
| Difficulty design | PENDING | |
| Compliance pre-review | PENDING | |
| Instruction Reviewer | PENDING | |
| Documentation Reviewer | PENDING | |
| Comprehensive Reviewer | PENDING | |
| Pre-LLMaJ aggregate | PENDING | |
| Q8 GPT Perspective Simulation | PENDING | diagnostic only |
| Q8 Claude Perspective Simulation | PENDING | diagnostic only |
| Harbor LLMaJ | PENDING | |
| Difficulty trials | PENDING | |
| GPT-5.5 difficulty ×5 | PENDING | |
| Claude Opus 4.8 difficulty ×5 | PENDING | |
| Combined difficulty ×10 | PENDING | |
| Per-test solvability 1/10 | PENDING | |
| Trial Analysis | PENDING | |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Latest CI

- Workflow: `none reconciled locally`
- Run ID: `none`
- Run number: `none`
- Job ID: `none`
- Commit/head SHA: `88e17620d0a13530127d61849557ec01ecdb1687` (control-plane HEAD at resume)
- Artifact ID(s): `none`

## Current blocker

Generate and execute independent Q4 (`spec-test-contract`) and Q6 (`production-logic`) packets in separate cold chats bound to task commit `582e0209de4595e14aecff692376800f209a610b`. This producer/orchestrator chat must not issue Q4/Q6 PASS.

## Root-cause classification

- Owner: CI Orchestrator / Submission Controller
- Classification: `none`
- Evidence: oracle job `2026-08-16__15-47-37` reward 1; nop job `2026-08-16__15-49-48` reward 0; python_loc=3011

## Next action

Open two fresh cold chats with the generated Q4 and Q6 packets under `.terminus/reviews/django-checkout-failover-ha/582e0209de4595e14aecff692376800f209a610b/`. Return results to the orchestrator for freshness validation. Do not run Q4/Q6 in the producer chat.

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Scope hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | | | 2.2 | 2.2 | 1.1 | | n/a | | PENDING | | blocked on honest freeze |
| Q6 Production Logic Auditor | | | 2.2 | 2.2 | 1.1 | | | | PENDING | | |
| Task Architect | | | | | | | | | PENDING | | |
| Verifier Engineer | | | | | | | | | PENDING | | |
| Originality | | | | | | | | | REVISE | | prior destemplate |
| Difficulty design | | | | | | | | | PENDING | | |
| Compliance pre-review | | | | | | | | | PENDING | | |
| Instruction | | | | | | | | | PENDING | | |
| Documentation | | | | | | | | | PENDING | | |
| Comprehensive Reviewer | | | | | 1.0 | | | | PENDING | | |
| Q8 GPT Perspective Simulation | | | | | 1.0 | | | | PENDING | | diagnostic only |
| Q8 Claude Perspective Simulation | | | | | 1.0 | | | | PENDING | | diagnostic only |
| Trial Analysis | | | | | | | | | PENDING | | |
| Final Compliance | | | | | | | | | PENDING | | |
| Final Human Quality | | | | | | | | | PENDING | | |

## Quality interlock checkpoint

- Q1 spec-gap status/evidence: `PENDING`
- Q2 verifier-coverage status/evidence: `PENDING`
- Q3 ambiguity status/evidence: `PENDING`
- Q7 format status/evidence: `PENDING`
- Q5 Oracle/runtime repair evidence: `none`
- Q4 review ID/result: `none`
- Q4 verdict/confidence/evidence: `PENDING`
- Q4 exhaustiveness: `INCOMPLETE`
- Q6 review ID/result: `none`
- Q6 verdict/confidence/evidence: `PENDING`
- Q6 production scope hash: `pending`
- Q6 scope reuse: `none`
- Quality interlock: `PENDING`

## Comprehensive reviewer checkpoint

- Review ID: `none`
- Result path: `none`
- Task commit: `7d88c647d3967e9988d2cd4fa13723a8f1989097`
- Role contract hash: `none`
- Checklist snapshot: `2026-08-08-user-supplied`
- Policy freshness: `UNVERIFIED`
- Checklist total: `unknown`
- Checklist coverage: `0`
- Recommendation: `INSUFFICIENT_EVIDENCE`
- High failures: `0`
- Medium failures: `0`
- Low failures: `0`
- Special trial revision flags: `none`
- Test-quality eval dispositions: `none`
- Trial-analysis dispositions: `none`
- Policy conflicts: `none`

## Pre-LLMaJ checkpoint

- Aggregate: `PENDING`
- Aggregate path: `none`
- Task commit: `7d88c647d3967e9988d2cd4fa13723a8f1989097`
- Panel policy: `2.2`
- Static check: `PENDING`
- Quality interlock: `PENDING`
- Comprehensive Reviewer: `INSUFFICIENT_EVIDENCE`
- Checklist coverage: `0`
- Adjudications: `none`
- Open findings: `production_logic scale`
- Policy conflicts: `none`

## Q8 model-perspective simulation checkpoint

- Task commit: `7d88c647d3967e9988d2cd4fa13723a8f1989097`
- GPT perspective review ID/result: `none`
- GPT execution: `PENDING`
- GPT final verifier result: `none`
- GPT predicted signal: `NOT_MEASURABLE`
- Claude perspective review ID/result: `none`
- Claude execution: `PENDING`
- Claude final verifier result: `none`
- Claude predicted signal: `NOT_MEASURABLE`
- Cross-perspective comparison: `n/a`

## Difficulty / solvability checkpoint

- Task commit: `7d88c647d3967e9988d2cd4fa13723a8f1989097`
- GPT-5.5 trials completed: `0`
- GPT complete passes: `0`
- Claude Opus 4.8 trials completed: `0`
- Claude complete passes: `0`
- Combined trials completed: `0`
- Combined complete passes: `0`
- Combined complete pass rate: `0`
- Measured tier: `NOT_MEASURED`
- Verifier cases at 0/10: `none`
- Difficulty artifact(s): `none`
- Result freshness: `NOT_RUN`
- Trajectory review IDs/paths: `none`
- Solvability policy: `every individual verifier case passes at least once across the combined 10 official trials`

## Adjudication ledger

| Adjudication ID | Dispute | Decision | Evidence | Recheck |
| --- | --- | --- | --- | --- |

## Policy-conflict ledger

| Conflict ID | Source A | Source B | Affected Gate | Impact | Resolution/status |
| --- | --- | --- | --- | --- | --- |

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- DJ-A only; `large_system_strict`; artifacts `["/app/ha"]`; sqlite primary/standby + `pins` cache; single dump `failover-status.json`; manage.py operators; writers do not self-certify Q4/Q6.
- Complexity validator PASS that depends on seed SQL LOC is not acceptance evidence for production scale.
- Do not claim durable `FROZEN_CANDIDATE` acceptance until the expanded task tree is committed and Q4/Q6 packets bind that SHA.
- Oracle/NOP evidence for this freeze attempt: `jobs/2026-08-16__15-47-37` (1) and `jobs/2026-08-16__15-49-48` (0).

## Known non-task infrastructure facts

- Workspace root `TerminalBench` is not a git repo; git lives under `Terminus-Edition-3/`.
- Unrelated dirty/untracked work exists on `main` (`codecommit-iam-merge-fence`, `webhook-outbox-delivery-plane`); leave it untouched.

## Attempts / changes

Newest first; keep only meaningful state-changing attempts.

- `582e0209de4595e14aecff692376800f209a610b` — ENVIRONMENT_BUILD modules + `.gitattributes` LF pins; freeze SHA for Q4/Q6.
- `2026-08-16` Harbor oracle `jobs/2026-08-16__15-47-37` → reward **1** (36/36). Harbor nop `jobs/2026-08-16__15-49-48` → reward **0**. Fixed CRLF on shebang scripts after first oracle `RewardFileNotFoundError`.
- `2026-08-16` ENVIRONMENT_BUILD slice — reachable HA modules; python_loc ~3011.
- `2026-08-16` controller resume — blocked premature Q4 on seed-inflated LOC.
- `7d88c64` — initial django ha + destemplate.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
