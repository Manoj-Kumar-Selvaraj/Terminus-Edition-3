# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `terraform-aws-ec2-fenced-fleet-rollout`
- Controller state: `ARCHITECTING`
- Working branch: `main`
- Pull request: none
- Current task commit: `4e715965bd1819e66c5705e70e538dc66dfbb1d3` (task tree; HEAD `02968862b6e0c36271370b97d1c75bdbeb9b9978` includes later unrelated tasks)
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
| Creator Complexity Gate | PENDING | required for strict large-system profile |
| Preflight/static | PENDING | |
| Ruff verifier | PENDING | |
| STB auth/AI credentials | PENDING | infrastructure dependency; not itself submission proof |
| Oracle = 1 | FAIL | Harbor 0.21 `jobs/fleet-bootstrap/oracle/2026-08-17__22-04-53` RewardFileNotFoundError; agent `python3\r` shebang (CRLF) |
| NOP = 0 | PENDING | not run; blocked on oracle harness |
| Q4 Spec-Test Contract Reviewer | PENDING | packet-bound independent exhaustive quality-interlock review; exact current task commit |
| Q4 Adjudicated Closure | NOT_APPLICABLE | only after Protocol circuit-breaker + Q4_CLOSURE_POLICY activation |
| Q6 Production Logic Auditor | PENDING | packet-bound independent quality-interlock review; exact task commit or Protocol-valid unchanged production scope |
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
- Run ID: `jobs/fleet-bootstrap/oracle/2026-08-17__22-04-53`
- Commit/head SHA: `02968862b6e0c36271370b97d1c75bdbeb9b9978`
- Artifact ID(s): none (reward file missing)

## Current blocker

From-scratch rebuild in progress: prior bulk tree never passed creation gates (no session/design, CRLF scripts, class-based tests invisible to F2P counter, starter LOC far below 3000, HCL grep for moved blocks).

## Root-cause classification

- Owner: PRODUCER (Environment Builder / Verifier Author)
- Classification: `oracle_runtime` plus `format_compliance` / `environment_gap`
- Evidence: `jobs/fleet-bootstrap/oracle/2026-08-17__22-04-53/terraform-aws-ec2-fenced-fleet-r__r7ZBAyi/agent/oracle.txt` (`python3\r`); `exception.txt` RewardFileNotFoundError

## Next action

Materialize the approved architecture + defect topology: multi-package Go controller, IPAM sqlite, LF scripts, F2P/P2P top-level tests, then complexity/authenticity/Harbor.

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

## Known non-task infrastructure facts

- Prefer Harbor `0.21` at `C:\Users\Manoj\AppData\Roaming\uv\tools\snorkelai-stb\Scripts\harbor.exe`.
- Procedural isolation only in this Auto chat (producer+controller combined by user request).

## Attempts / changes

- `4e715965` — bulk add of the original stub task — never sessioned.
- `2026-08-17` Harbor oracle — CRLF shebang, no reward file.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
