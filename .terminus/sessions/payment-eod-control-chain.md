# Terminus Task Session

Session schema version: `2.0`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Last checkpoint task commit: `38eb445e976be327a8fb2064ff896df24a85cd7d`
- Agent-system policy: `2.0`
- Specialist prompt policy: `2.0`
- Pre-LLMaJ panel policy: `2.0`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Preflight/static | PASS | run `31200979809` (#49), task functional structure unchanged |
| Ruff verifier | PASS | run `31200979809` (#49) |
| STB auth/AI credentials | BLOCKED | Edition-2 Portkey refresh ceiling reached |
| Oracle = 1 | PASS | run `31200979809` (#49) |
| NOP = 0 | PASS | run `31200979809` (#49) |
| Pre-LLMaJ panel | STALE | previous baseline used weaker reviewer policy; v2.0 requires fresh independent panel |
| Task Architect | STALE | rerun under v2.0 bounded/evidence protocol |
| Verifier Engineer | STALE | previous provisional review predates v2.0 independent req↔test method |
| Originality & Authenticity | STALE | prior REVISE remains useful evidence but must be cold-rerun under v2.0 |
| Difficulty design | STALE | prior Advanced candidate assessment predates v2.0 policy |
| Compliance pre-review | PENDING | v2.0 review not run |
| Instruction Reviewer | STALE | prior PASS predates v2.0 reviewer policy |
| Documentation Reviewer | STALE | prior REVISE predates v2.0 reviewer policy |
| Harbor LLMaJ | STALE | last PASS was before instruction rewrite; blocked until Pre-LLMaJ PASS |
| Difficulty 5x | NOT_RUN | blocked by Pre-LLMaJ + credentials |
| Per-test 1/5 minimum | NOT_RUN | difficulty not run |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Latest meaningful functional evidence

- Run `31200979809` (#49): Oracle=1, NOP=0, Harbor LLMaJ PASS for the earlier instruction version; the then-old evidence-manifest step failed after substantive gates.
- `38eb445`: rewrote `instruction.md` to ~126 words; this invalidated Harbor text review but did not change functional task behavior.
- Later CI attempts were infrastructure-only failures: Snorkel HTTP 502, Harbor read timeout, then Portkey maximum refresh limit 20.

## Current blocker

Two independent blockers:

1. Reviewer/control-plane policy changed materially to v2.0. All prior semantic Pre-LLMaJ judgments are stale and must be rerun independently with evidence/confidence/adjudication rules.
2. Fresh hosted runners cannot generate another Portkey key under the current Edition-2 refresh allowance, so expensive Harbor/difficulty runs should not be retried yet.

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `review_disagreement/policy_staleness + ci_infrastructure`
- Evidence: agent policy v2.0 files plus run `31201744808` attempt 3 for credential ceiling.

## Review evidence ledger

| Review | Review ID | Task commit | Policy version | Verdict | Confidence | Evidence status | Finding IDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Task Architect | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | n/a |
| Verifier Engineer | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | n/a |
| Originality | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | prior: duplicate LOW, template MEDIUM, realism HIGH |
| Difficulty design | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | prior: Advanced candidate |
| Compliance | none | | v2.0 | PENDING | | | |
| Instruction | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | prior: ~126 words, human signal HIGH |
| Documentation | legacy | `38eb445` | pre-v2 | STALE | n/a | n/a | prior: README synthetic/rubric-like |
| Human Quality | none | | v2.0 | PENDING | | | |

## Pre-LLMaJ checkpoint

- Aggregate: `STALE`
- Task commit: `38eb445e976be327a8fb2064ff896df24a85cd7d`
- Panel policy: `2.0`
- Static check: `PASS` from prior task validation for unchanged functional files; agent-system static CI is separate.
- Adjudications: `none`
- Open findings to re-evaluate cold: artificial one-bug-per-requirement/template signal; README/explanation AI/rubric voice; final instruction fairness under v2.0.

Harbor LLMaJ must not run until fresh aggregate Pre-LLMaJ is PASS.

## Difficulty checkpoint

- Task commit: `38eb445e976be327a8fb2064ff896df24a85cd7d`
- Suite/model: `NOT_RUN`
- Complete-run passes: `NOT_RUN`
- Complete-run failures: `NOT_RUN`
- Verifier test cases at 0/5: `NOT_RUN`
- Difficulty evidence artifact: `none`
- Result freshness: `NOT_RUN`
- Trajectory review IDs: `none`

Acceptance: at least two complete failures; every verifier test passes at least once; 4/5 or 5/5 complete passes is too easy; any test at 0/5 blocks.

## Adjudication ledger

| Adjudication ID | Dispute | Decision | Evidence | Recheck |
| --- | --- | --- | --- | --- |
| none | | | | |

## Circuit breakers

- Status: `TRIPPED`
- Trigger: repeated credential/infrastructure retries ended at Portkey maximum refresh limit 20.
- Attempts: multiple validation retries after run #49.
- Required strategy change/evidence: establish reusable approved AI credentials or a changed eligible allocation before another Harbor/difficulty run.

Do not repeat the refresh strategy until the dependency changes.

## Durable decisions

- Agent/reviewer policy v2.0 uses one manager, bounded specialist contexts, cold independent reviewers, evidence/confidence/INSUFFICIENT_EVIDENCE, adjudication and circuit breakers.
- Instruction Writer/Reviewer and Documentation Writer/Reviewer are separate producer/reviewer roles.
- Originality review is mandatory before difficulty.
- Pre-LLMaJ must PASS before Harbor `check`.
- Harbor misses become calibration + reviewer regression cases.
- Public/golden/web material is calibration data, never authority over Edition 3 rules.
- GitHub + CI/artifacts + versioned session evidence are durable state; chat is replaceable.
- Infrastructure failures are not task/verifier failures.

## Known infrastructure facts

- CI uses `snorkelai-stb==2.4.1`.
- Until Edition 3 allocation exists, workflow defaults to Edition-2 Portkey project `bfe79c33-8ab0-4061-9849-08d3207c9927`.
- Never store credential values in repository files or chat.
- Repeated `stb keys refresh` on fresh hosted runners has exhausted the current allowance.

## Next action

Rerun the v2.0 Pre-LLMaJ reviewers as independent cold reviews on the current task commit, using bounded evidence packets and frozen reports. Resolve any material reviewer conflict through Adjudicator. Only after aggregate PASS should task structural/prose fixes be finalized and Harbor retried; Harbor/difficulty remains additionally blocked on a reusable credential path.

## Do not retry blindly

- Do not reuse pre-v2 semantic PASS/REVISE results as current verdicts.
- Do not run Harbor before Pre-LLMaJ v2 PASS.
- Do not repeat Portkey refresh while the circuit breaker remains tripped.
- Do not weaken verifier/task logic because of auth/network/tool failures.

## Resume rule

A new controller must follow `.terminus/CONTINUE_SESSION.md`, load current v2.0 policy files, this checkpoint, current task/PR/Actions/artifacts, reconcile versions/evidence, and resume from the first stale/failed gate.
