# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `terraform-aws-ec2-fenced-fleet-rollout`
- Controller state: `DETERMINISTIC_PASS` (uncommitted; freeze blocked until user asks for a commit)
- Working branch: `main`
- Pull request: none
- Current task commit: uncommitted rebuild on top of `4e715965bd1819e66c5705e70e538dc66dfbb1d3`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 02968862b6e0c36271370b97d1c75bdbeb9b9978
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; AGENT_SYSTEM.md 2.5; CREATION_CONTROLLER.md; CREATION_PIPELINE.md; PRODUCTION_AUTHENTICITY.md; INSTRUCTION_POLICY.md; terraform-edition-2-to-3.mdc §12; .cursor/rules/terminus-edition-3-*.mdc
ACTIVE_VALIDATORS: validate_task_complexity.py; validate_runtime_authenticity.py; Harbor 0.21 separate-verifier; Ruff on tests; digest-pinned images
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: environment_mode=separate; network_mode=public; agent timeout 10800; canonical golang:1.24-bookworm digest; Terraform 1.9.8 pinned; tmux+asciinema in agent image
KNOWN_POLICY_CONFLICTS: none
```

Profile justification: frontier operational work package (fenced EC2 fleet rollout + live control plane). Not a localized one-file bug.

`task_kind=software` (not `infrastructure` 30–50 TF resources): a payments ASG naturally has a launch template, ASG, SG, IAM, instance profile, volumes, and attachments. Padding extra AWS resources would be decorative.

Stateful 10k–20k records: org IPAM subnet catalog (`subnets` table) is reachable from validation/placement. A six-instance fleet inventory would be an unrealistic primary table.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | producer evidence; all graded behavior discoverable without test-dump prose |
| Q2 Verifier Coverage Repair | PENDING | producer evidence; every material solver-visible requirement meaningfully tested |
| Q3 Spec Ambiguity Repair | PENDING | producer evidence; no grading-relevant ambiguity |
| Q7 Task Format Enforcer | PENDING | exact current task/task.toml/Docker/verifier/solution/package rules |
| Creator Complexity Gate | PASS | `python .terminus/validate_task_complexity.py` — substantive_loc=3248, defects=24, RC=8, F2P=26, P2P=2 |
| Preflight/static | PENDING | Harbor `tasks check` not yet run |
| Ruff verifier | PASS | `uvx ruff==0.8.4 check tests/test_outputs.py` — All checks passed |
| STB auth/AI credentials | PENDING | infrastructure dependency; not itself submission proof |
| Oracle = 1 | PASS | Harbor 0.21 `jobs/fleet-rebuild-4/2026-08-17__23-39-25` mean 1.000; 28/28 pytest passed |
| NOP = 0 | PASS | Harbor 0.21 `jobs/fleet-nop-2/2026-08-17__23-45-23` mean 0.000; 25 failed / 3 passed (P2P artifacts + IPAM + forged-report overwrite path) |
| Q4 Spec-Test Contract Reviewer | PENDING | blocked on committed freeze; packet generator refuses dirty task tree |
| Q4 Adjudicated Closure | NOT_APPLICABLE | only after Protocol circuit-breaker + Q4_CLOSURE_POLICY activation |
| Q6 Production Logic Auditor | PENDING | blocked on committed freeze |
| Quality Interlock | PENDING | Q4 current PASS + Q6 current/scope-preserved PASS |
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

## Latest CI

- Workflow: local Harbor 0.21 only
- Oracle: `jobs/fleet-rebuild-4/2026-08-17__23-39-25` reward 1.0, 28 passed in 141.84s
- NOP: `jobs/fleet-nop-2/2026-08-17__23-45-23` reward 0.0, 25 failed / 3 passed
- Authenticity: `validate_runtime_authenticity.py` PASS (12000 subnets)

## Current blocker

Deterministic gates are green on the uncommitted rebuild. Q4/Q6 packets cannot be generated until the task tree is committed (`new_review_packet.py` refuses a dirty tree). User has not asked for a commit.

## Root-cause classification

- Owner: PRODUCER (Environment Builder / Verifier Author)
- Classification: `resolved_oracle_runtime` — prior CRLF shebang, inventory slice panic, and IPAM-missing AMI in the target-release fixture
- Evidence: oracle 1.0 after `jobs/fleet-rebuild-4`; NOP 0.0 after `jobs/fleet-nop-2`

## Next action

Commit the rebuilt task when the user asks, then freeze and run packet-bound Q4 then Q6 in a separate reviewer chat (this Auto chat authored the rebuild).

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Scope hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | | | 2.2 | 2.2 | 1.1 | | n/a | | PENDING | | exhaustive one-pass review required |
| Q6 Production Logic Auditor | | | 2.2 | 2.2 | 1.1 | | | | PENDING | | production scope hash required |

## Quality interlock checkpoint

- Quality interlock: `PENDING`

## Policy-conflict ledger

| Conflict ID | Source A | Source B | Affected Gate | Impact | Resolution/status |
| --- | --- | --- | --- | --- | --- |

## Circuit breakers

- Status: `CLEAR`
- Trigger: none
- Attempts: 0
- Required strategy change/evidence: none

## Decisions that must survive chat changes

- Recreate under `large_system_strict` rather than certify the bulk-committed stub.
- Do not restore deleted Edition 2 `terraform-aws-ec2-module-rollout-recovery`.
- Verifier-owned control plane remains `/opt/ec2-controlplane`; agents cannot rewrite observed inventory by swapping that binary (hash check).
- Tests judge Terraform via `terraform show -json` / live control-plane inventory, not HCL greps.
- Unrelated dirty trees (tenant-catalog, yard-gate, event-time) stay untouched.
- Operator is `/app/bin/fenced-fleet-rollout` wrapping `/app/scripts/rollout_operator.py` (LF).
- Starter packages keep observable defects; spec packages exist for LOC/complexity and must not be invoked on live journal paths.

## Known non-task infrastructure facts

- Prefer Harbor `0.21` at `C:\Users\Manoj\AppData\Roaming\uv\tools\snorkelai-stb\Scripts\harbor.exe`.
- Procedural isolation only in this Auto chat (producer+controller combined by user request).

## Attempts / changes

- `4e715965` — bulk add of the original stub task — never sessioned.
- `2026-08-17` Harbor oracle `jobs/fleet-bootstrap` — CRLF shebang, no reward file.
- Rebuild: LF operator, F2P/P2P tests, IPAM 12k, Go controller + Terraform solution, complexity 3248.
- `jobs/fleet-rebuild` — inventory `value[:4]` panic on 3-char strings.
- `jobs/fleet-rebuild-2` — 27/28; target-release AMI `ami-0feed20260620` absent from IPAM.
- `jobs/fleet-rebuild-3` — oracle 1.000 (28 passed).
- `jobs/fleet-rebuild-4` — oracle 1.000 after identity-version F2P tighten.
- `jobs/fleet-nop` then `jobs/fleet-nop-2` — NOP 0.000.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
