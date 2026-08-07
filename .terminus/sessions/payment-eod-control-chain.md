# Terminus Task Session

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `VALIDATING`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#1`
- Last checkpoint commit: `c582aebdb260532c2fa95994ab7ef9f4c712b42c`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PASS | Workflow run 31197092691 |
| Ruff verifier | PASS | Workflow run 31197092691 |
| STB auth/AI credentials | PASS | Login and Edition-2 Portkey refresh succeeded in run 31197092691 |
| Oracle = 1 | FAIL | Harbor ended with RuntimeError; no reward.txt produced |
| NOP = 0 | NOT_RUN | blocked by Oracle |
| LLMaJ | NOT_RUN | blocked by Oracle |
| Difficulty 5x | NOT_RUN | normal validation not green |
| Per-test 1/5 minimum | NOT_RUN | difficulty not run |
| Compliance audit | PENDING | final audit not run |
| Human quality audit | PENDING | final audit not run |
| Final package | PENDING | task not submission-ready |

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31197092691`
- Run number: `33`
- Validate job ID: `92927923888`
- PR head commit: `c582aebdb260532c2fa95994ab7ef9f4c712b42c`
- Validation artifact ID: `9001287407`
- Validation artifact name: `terminus-validation-payment-eod-control-chain-31197092691-1`

## Current blocker

Oracle reaches Harbor but Harbor raises a `RuntimeError` before the verifier produces `reward.txt`. The current Actions log only surfaces the aggregate exception; the uploaded validation artifact contains the Harbor result/trajectory files that must be inspected to identify the exact runtime cause.

There is also a secondary CI evidence-manifest bug: the workflow uses `find ... -printf -- '- %P\n'`, which this runner parses incorrectly. This does not cause the Oracle failure but should be fixed before the next validation run so evidence summarization remains green.

## Root-cause classification

- Owner: `CI Orchestrator` until the Harbor RuntimeError is classified from artifact evidence.
- Classification: `ci_infrastructure` (provisional; must be reclassified after reading Harbor result/trajectory evidence).
- Evidence: workflow run `31197092691`, validate job `92927923888`, artifact `9001287407`.

## Next action

Inspect the Oracle Harbor `result.json` and trajectory/log files from artifact `9001287407`, identify the exact RuntimeError, route it to CI Orchestrator / Task Architect / Verifier Engineer as appropriate, fix the evidence-manifest shell bug, push, retrigger validation, and continue until Oracle=1, NOP=0, and LLMaJ pass.

## Difficulty checkpoint

- Suite/model: `NOT_RUN`
- Complete-run passes: `NOT_RUN`
- Complete-run failures: `NOT_RUN`
- Verifier test cases at 0/5: `NOT_RUN`
- Difficulty evidence artifact: `none`
- Result freshness: `NOT_RUN`

Policy when difficulty begins:
- 4/5 or 5/5 complete solutions passing is too easy and requires recalibration.
- At least two complete attempts must fail.
- Every individual verifier test case must pass in at least one of five attempts.
- Any verifier test case at 0/5 is an acceptance blocker and requires trajectory analysis plus remediation.

## Decisions that must survive chat changes

- Use current Terminus Edition 3 rule files and `.terminus/AGENT_SYSTEM.md` as authoritative local tasking guidance.
- Use the seven-role agent system: Task Architect, Verifier Engineer, Compliance Auditor, Difficulty Reviewer, Human Quality Reviewer, Trajectory Analyst, CI Orchestrator / Submission Controller.
- The CI Orchestrator owns the active loop and routes evidence to specialist roles; the user should not need to manually choose agents for each failure.
- Keep 25 pinned Terminal-Bench golden references under `.terminus/GOLDEN_TASKS.md` for calibration only, never as templates to copy.
- GitHub repository + Actions evidence are the durable operational source of truth; chat history is replaceable.
- After a substantive task/verifier/instruction/environment change, previous difficulty results become stale and normal validation must run again.

## Known non-task infrastructure facts

- CI currently uses `snorkelai-stb==2.4.1` as the known-good version.
- Until an Edition 3 Portkey project is allocated, the workflow defaults to the eligible Edition 2 Portkey project ID `bfe79c33-8ab0-4061-9849-08d3207c9927`.
- `SNORKEL_API_KEY` is provided via GitHub Actions secret; never store its value in repository files or chat.
- GitHub-hosted runners are used; no self-hosted runner is required.

## Attempts / changes

- Run `31197092691` — STB install/login and AI credential refresh succeeded; Oracle reached Harbor but ended with one `RuntimeError`; no reward.txt; evidence artifact `9001287407` uploaded.
- Earlier credential debugging established that Oracle itself requires AI credentials; credential refresh must occur before Oracle.
- Earlier Edition 3 Portkey attempt returned unauthorized; continue using Edition 2 default until allocation changes.

## Do not retry blindly

- Do not switch CI back to the unallocated Edition 3 Portkey project unless account allocation has actually changed.
- Do not treat a missing Oracle reward as a verifier failure until Harbor's RuntimeError is inspected.
- Do not run difficulty while Oracle/NOP/LLMaJ normal validation is not green.

## Resume rule

A new chat/controller must first read `.terminus/CONTINUE_SESSION.md`, `.terminus/AGENT_SYSTEM.md`, this checkpoint, the current task files, PR #1, and the latest Actions evidence. Live GitHub/CI evidence overrides stale values in this file; update this checkpoint before making new task changes when they disagree.
