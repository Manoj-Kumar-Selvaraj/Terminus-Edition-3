# Creation session — django-checkout-failover-ha

Controller: this chat (producer / orchestrator). Independent Q4/Q6/Pre-LLMaJ reviewers must run in other chats.

## Identity

- Task: `django-checkout-failover-ha`
- Branch: `task/django-checkout-failover-ha`
- Profile: `large_system_strict`
- Taxonomy: Software / Systems
- Artifact root: `/app/ha`

## Controller state

`AUTHORING` — destemplate slice applied. Local oracle 36/36; Harbor oracle 1.0 (`2026-08-09__18-04-41`) / NOP 0.0 (`2026-08-09__18-06-49`).

## Scenario freeze

- Approved candidate: DJ-A (mid-cutover dual-AZ Django checkout after primary promotion).
- Operator surface: `manage.py sync_standby`, `cutover --node`, `dump_failover`.
- Output: `/app/ha/out/failover-status.json` only.
- Evidence: `/app/ha/notes/oncall.md`, `/app/ha/logs/captured/shopdesk-error.log`.
- Lab truth: two SQLite shop files + cache alias `pins` (not Postgres/Redis).

## Creation pipeline checkpoint

| Step | Owner | Status |
| --- | --- | --- |
| Scenario Researcher | this chat | DJ-A recorded |
| System Architect / Environment | this chat | destemplated Django manage.py surface |
| Defect Designer | this chat | 26 manifestations / 7 clusters |
| Oracle Author | this chat | `solution/solve.sh` + files |
| Verifier Author | this chat | 30 F2P + 6 P2P over WSGI/manage.py |
| Instruction Author | this chat | two paragraphs, ticket voice |
| Documentation | this chat | `docs/runbook.md` + README |
| Complexity / authenticity gates | this chat | PASS after destemplate |
| Local pytest oracle (temp tree) | this chat | 36 passed after destemplate |
| Harbor oracle / NOP | this chat | oracle 1.0 (`2026-08-09__18-04-41`); NOP 0.0 (`2026-08-09__18-06-49`) |
| Independent Q4 / Q6 | other chats | not started |
| Pre-LLMaJ | other chats | not started |

## Root-cause classification

- Owner: Scenario Researcher
- Classification: none
- Evidence: `.terminus/research/django-checkout-failover-ha.md`

## Next action

Route independent Q4/Q6. Do not self-certify Pre-LLMaJ. Difficulty trials after Pre-LLMaJ.

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Role contract hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | | | | | 1.0 | | | PENDING | | |
| Q6 Production Logic Auditor | | | | | 1.0 | | | PENDING | | |
| Task Architect | | | | | | | | PENDING | | |
| Verifier Engineer | | | | | | | | PENDING | | |
| Originality | | | | | | | | REVISE (prior chat) | destemplate applied | house-shell noun-swap |
| Difficulty design | | | | | | | | PENDING | | |
| Compliance pre-review | | | | | | | | PENDING | | |
| Instruction | | | | | | | | PENDING | | |
| Documentation | | | | | | | | PENDING | | |
| Comprehensive Reviewer | | | | | 1.0 | | | PENDING | | |
| Q8 GPT Perspective Simulation | | | | | 1.0 | | | PENDING | | diagnostic only |
| Q8 Claude Perspective Simulation | | | | | 1.0 | | | PENDING | | diagnostic only |
| Trial Analysis | | | | | | | | PENDING | | |
| Final Compliance | | | | | | | | PENDING | | |
| Final Human Quality | | | | | 1.0 | | | PENDING | | |

## Quality interlock checkpoint

- Quality interlock: `PENDING`

## Pre-LLMaJ checkpoint

- Aggregate: `PENDING`

## Difficulty / solvability checkpoint

- Measured tier: `NOT_MEASURED`

## Circuit breakers

- Status: `CLEAR`

## Decisions that must survive chat changes

- DJ-A only; large_system_strict; artifacts `["/app/ha"]`; sqlite primary/standby + `pins` cache; single dump `failover-status.json`; no ha-ctl / dual health+reconcile shell; writers in this chat do not self-certify Q4/Q6.
- Destemplate: ticket voice, manage.py operators, HTTP/manage.py tests, honest sqlite/cache metadata.

## Attempts / changes

- Authored full task tree on `task/django-checkout-failover-ha`.
- First Harbor oracle 1.0 / NOP 0.0 before destemplate.
- Destemplate slice: removed jetstream/payment-eod house shell (ha-ctl, dual JSON dumps, ha-contract).

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
