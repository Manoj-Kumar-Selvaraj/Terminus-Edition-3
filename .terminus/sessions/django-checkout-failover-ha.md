# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `django-checkout-failover-ha`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `f9022bd10e98152efcc245a1a0a738bf29f77a80`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | DONE | pay commit-fence + blank attempt documented in instruction/runbook |
| Q2 Verifier Coverage Repair | DONE | phantoms dropped/rewritten; /readyz pins+repeats; accepting_checkout conjuncts added (42 tests) |
| Q3 Spec Ambiguity Repair | DONE | live `/readyz` vs dump `accepting_checkout` authority split in runbook + readiness_policy |
| Q7 Task Format Enforcer | PENDING | layout present; `tests/test_ha.py` not `test_outputs.py`; no CTRF flag |
| Creator Complexity Gate | PASS | reachable Python non-blank LOC excl. `generate_seed.py` ≈ 3646 after heal_plan |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | |
| Oracle = 1 | PASS | Harbor job `jobs/2026-08-16__17-09-55` trial `django-checkout-failover-ha__v78pfFk` reward.txt=`1`; 44/44 pytest |
| NOP = 0 | PASS | Harbor job `jobs/2026-08-16__17-11-37` trial `django-checkout-failover-ha__DxQFQcm` reward.txt=`0` |
| Q4 Spec-Test Contract Reviewer | PENDING | packet `.terminus/reviews/django-checkout-failover-ha/f9022bd1/django-checkout-failover-ha-f9022bd1-spec-test-contract-c6e2481129.packet.json` |
| Q6 Production Logic Auditor | PENDING | packet `.terminus/reviews/django-checkout-failover-ha/f9022bd1/django-checkout-failover-ha-f9022bd1-production-logic-b02c7d085b.packet.json` |
| Quality Interlock | PENDING | blocked until cold Q4+Q6 PASS on freeze `f9022bd1` |
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

None for deterministic gates. Awaiting Auto/inherit cold Q4 + Q6 on freeze `f9022bd1`.

## Root-cause classification

- Owner: Q2 Verifier + Environment Builder (consolidated with Q6 padding repair)
- Classification: `verifier_gap` / `spec_ambiguity` + `production_logic`
- Evidence: Q4 `...-spec-test-contract-8ff470e1b2.json`; Q6 `...-production-logic-03ac8bd7ce.json`

## Next action

Await Auto-mode cold Q4/Q6 for freeze `f9022bd1`. Subagents must use `model: inherit` only. Do not self-certify Quality Interlock.

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Scope hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | django-checkout-failover-ha-8dc0203f-spec-test-contract-8ff470e1b2 | 8dc0203f55e6112a093bfc680c831f6f5b357f9b | 2.2 | 2.2 | 1.1 | c860dfe8b8ed0a04c729e4d6a828741b206b7067a780863ec7b22ee09d02c5a0 | n/a | `.terminus/reviews/django-checkout-failover-ha/8dc0203f/django-checkout-failover-ha-8dc0203f-spec-test-contract-8ff470e1b2.json` | REVISE | HIGH | blocking Q4-F1..F4; exhaustiveness COMPLETE |
| Q6 Production Logic Auditor | django-checkout-failover-ha-8dc0203f-production-logic-03ac8bd7ce | 8dc0203f55e6112a093bfc680c831f6f5b357f9b | 2.2 | 2.2 | 1.1 | ee7d1cfd6e19fcc0e831cc75829457593d7410613c3b3fb811aef925e85a1607 | 5a9db7fc2c248c3aa962bad9e1734b83dca9eca5bade04e9c462874bfe04f412 | `.terminus/reviews/django-checkout-failover-ha/8dc0203f/django-checkout-failover-ha-8dc0203f-production-logic-03ac8bd7ce.json` | REVISE | HIGH | PADDING_RISK HIGH; ~2860 substantive LOC |
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

- Q1 spec-gap status/evidence: `DONE` (documented in instruction/runbook during repair)
- Q2 verifier-coverage status/evidence: `DONE` (42 tests; phantoms closed)
- Q3 ambiguity status/evidence: `DONE` (live /readyz vs dump accepting_checkout)
- Q7 format status/evidence: `PENDING`
- Q5 Oracle/runtime repair evidence: `none`
- Q4 review ID/result: `django-checkout-failover-ha-8dc0203f-spec-test-contract-8ff470e1b2` / `.terminus/reviews/django-checkout-failover-ha/8dc0203f/django-checkout-failover-ha-8dc0203f-spec-test-contract-8ff470e1b2.json`
- Q4 verdict/confidence/evidence: `REVISE` / `HIGH` / `SUFFICIENT`
- Q4 exhaustiveness: `COMPLETE` (BLOCKING_FINDING_IDS Q4-F1..F4)
- Q6 review ID/result: `django-checkout-failover-ha-8dc0203f-production-logic-03ac8bd7ce` / `.terminus/reviews/django-checkout-failover-ha/8dc0203f/django-checkout-failover-ha-8dc0203f-production-logic-03ac8bd7ce.json`
- Q6 verdict/confidence/evidence: `REVISE` / `HIGH` / `SUFFICIENT`
- Q6 production scope hash: `5a9db7fc2c248c3aa962bad9e1734b83dca9eca5bade04e9c462874bfe04f412`
- Q6 scope reuse: `none`
- Quality interlock: `REVISE`

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
- Oracle/NOP evidence after Q4/Q6 repair: `jobs/2026-08-16__16-37-20` (1, 42/42) and `jobs/2026-08-16__16-38-42` (0). Prior freeze evidence: `jobs/2026-08-16__15-47-37` (1) and `jobs/2026-08-16__15-49-48` (0).

## Known non-task infrastructure facts

- Workspace root `TerminalBench` is not a git repo; git lives under `Terminus-Edition-3/`.
- Unrelated dirty/untracked work exists on `main` (`codecommit-iam-merge-fence`, `webhook-outbox-delivery-plane`); leave it untouched.

## Attempts / changes

Newest first; keep only meaningful state-changing attempts.

- Q4 cold review REVISE via [Q4 Spec-Test Review](28c39e2a-fe36-4d30-be10-0581a7390e13) on freeze `8dc0203f` → `...-spec-test-contract-8ff470e1b2.json` (blocking F1–F4).
- Q6 cold review REVISE via [Q6 Production Logic Audit](7e44db88-f504-42b0-9e91-fdd37444a9ca) on freeze `8dc0203f` → `...-production-logic-03ac8bd7ce.json` (HIGH padding; ~2860 substantive LOC).
- Freeze `8dc0203f55e6112a093bfc680c831f6f5b357f9b` for post-repair Q4/Q6; packets under `.terminus/reviews/django-checkout-failover-ha/8dc0203f/`.
- Consolidated Q4/Q6 repair: stripped Defect/Starter diagnosis; split live `/readyz` vs dump `accepting_checkout`; wired `desk_state` + helpers into live paths (~3396 Python LOC); fixed phantoms and added readiness/dump coverage; solution reports/views/sessions/replica updated. Harbor oracle `jobs/2026-08-16__16-37-20` → **1** (42/42); nop `jobs/2026-08-16__16-38-42` → **0**.
- Q6 cold review REVISE via [Q6 Production Logic Audit](6db7aba3-2767-45ce-adf5-556dc06479e6) → `...-production-logic-4f058fe6e4.json` (HIGH padding; honest LOC below floor).
- Q4 cold review REVISE via [Q4 Spec-Test Review](dbc8029f-ac02-403d-ad04-9323313db645) → `...-spec-test-contract-3d991dfb3b.json`.
- `582e0209de4595e14aecff692376800f209a610b` — ENVIRONMENT_BUILD modules + `.gitattributes` LF pins; freeze SHA for Q4/Q6.
- `2026-08-16` Harbor oracle `jobs/2026-08-16__15-47-37` → reward **1** (36/36). Harbor nop `jobs/2026-08-16__15-49-48` → reward **0**. Fixed CRLF on shebang scripts after first oracle `RewardFileNotFoundError`.
- `2026-08-16` ENVIRONMENT_BUILD slice — reachable HA modules; python_loc ~3011.
- `2026-08-16` controller resume — blocked premature Q4 on seed-inflated LOC.
- `7d88c64` — initial django ha + destemplate.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
