# Terminus Task Session

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `VALIDATED`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Last checkpoint task commit: `d0751b1d72a85a103c60015e41ee1654981410a6`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PASS | run 31200979809 (#49) |
| Ruff verifier | PASS | run 31200979809 (#49) |
| STB auth/AI credentials | BLOCKED | later run attempt hit Portkey maximum refresh limit 20; prior successful runs prove credentials worked |
| Oracle = 1 | PASS | run 31200979809 (#49); also passed run 31201744808 attempt 2 |
| NOP = 0 | PASS | run 31200979809 (#49) |
| LLMaJ | PASS | run 31200979809 (#49) |
| Evidence manifest | PASS | fixed workflow; run 31201744808 attempts 1-3 prove manifest step succeeds |
| Difficulty 5x | NOT_RUN | blocked until reusable AI credentials avoid fresh refresh consumption |
| Per-test 1/5 minimum | NOT_RUN | difficulty not run |
| Compliance audit | PENDING | final audit not run |
| Human quality audit | PENDING | final audit not run |
| Final package | PENDING | task not submission-ready |

## Latest meaningful validation evidence

Successful task-gate run:
- Workflow run ID: `31200979809`
- Run number: `49`
- Validate job ID: `92940649690`
- PR head: `c1ee91a81071830aa9c2eab4f880a3484abb12e9`
- Result: Oracle PASS, NOP PASS, LLMaJ PASS. The job was red only because the old evidence-manifest shell command failed after all substantive gates had passed.

Evidence-manifest fix:
- Workflow commit: `3a881259758017973741eadc73e3a2a73cce23b4`
- Later runs show `Build validation evidence manifest` PASS.

Later infrastructure-only failures:
- Run `31201744808` attempt 1: Snorkel `/users/me` returned HTTP 502 before task execution.
- Run `31201744808` attempt 2: Oracle PASS; NOP Harbor call failed before trial execution with `The read operation timed out`.
- Run `31201744808` attempt 3: STB login PASS; Portkey refresh failed with `Maximum refresh limit (20) reached` before task execution.

## Current blocker

Fresh GitHub-hosted runners currently require `stb keys refresh`, and the active Edition-2 Portkey project/account has reached its maximum refresh count. Do not burn further runs by repeatedly refreshing credentials. The task itself is validated; the next infrastructure objective is reusable model credentials that can be injected securely from GitHub Secrets (or another approved durable credential mechanism) without generating a new Portkey key on every runner.

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `ci_infrastructure`
- Evidence: run `31201744808` attempt 3 shows `Maximum refresh limit (20) reached` in `Authenticate stb and refresh AI credentials`.
- Task edits required: `none`.

## Task fixes already completed

1. Environment Dockerfile now creates `/app/eod/state` before initializing SQLite.
2. Oracle solution paths use Harbor's `/solution` mount instead of `/oracle`.
3. Removed nonexistent `/solution/correct/payexec.cob` copy; the starter `PAYEXEC` program already satisfies its direct interface tests.
4. Oracle now copies corrected `paydup.cob`, `schema.sql`, and `run_eod.sh`, rebuilds sample state, and executes the corrected EOD flow.
5. Evidence-manifest shell enumeration was fixed and difficulty CI was aligned with the per-test 0/5 policy.

## Next action

Implement a secure reusable-AI-credential path for CI so fresh runners do not call Portkey refresh unnecessarily. Do not request or store secret values in chat or repository files. Once credentials are reusable, run one clean validation if needed, then run final five-trial difficulty calibration and inspect both complete-run distribution and per-verifier-test coverage.

## Difficulty checkpoint

- Suite/model: `NOT_RUN`
- Complete-run passes: `NOT_RUN`
- Complete-run failures: `NOT_RUN`
- Verifier test cases at 0/5: `NOT_RUN`
- Difficulty evidence artifact: `none`
- Result freshness: `NOT_RUN`

Acceptance policy:
- 4/5 or 5/5 complete solutions passing is too easy and requires recalibration.
- At least two of five complete attempts must fail.
- Every individual verifier test case must pass in at least one of five attempts.
- Any verifier test case at 0/5 is an acceptance blocker; analyze all relevant trajectories and repair the task/instruction/environment/verifier until no test remains 0/5.

## Decisions that must survive chat changes

- Use current Terminus Edition 3 rule files and `.terminus/AGENT_SYSTEM.md` as authoritative local tasking guidance.
- Use the seven-role agent system: Task Architect, Verifier Engineer, Compliance Auditor, Difficulty Reviewer, Human Quality Reviewer, Trajectory Analyst, CI Orchestrator / Submission Controller.
- The CI Orchestrator owns the active loop and routes evidence to specialist roles; the user should not need to manually choose agents for each failure.
- Keep 25 pinned Terminal-Bench golden references under `.terminus/GOLDEN_TASKS.md` for calibration only, never as templates to copy.
- GitHub repository + Actions evidence are the durable operational source of truth; chat history is replaceable.
- After a substantive task/verifier/instruction/environment change, previous difficulty results become stale and normal validation must run again.
- Infrastructure/network failures such as HTTP 502, read timeouts, or credential-generation quotas must not be treated as task/verifier failures.

## Known non-task infrastructure facts

- CI uses `snorkelai-stb==2.4.1` as the known-good version.
- Until an Edition 3 Portkey project is allocated, workflow defaults to Edition 2 Portkey project ID `bfe79c33-8ab0-4061-9849-08d3207c9927`.
- `SNORKEL_API_KEY` is injected via GitHub Actions secret; never store its value in repository files or chat.
- GitHub-hosted runners are used; no self-hosted runner is required.
- Repeated `stb keys refresh` calls consume a finite refresh allowance and are not a sustainable per-run authentication strategy.

## Attempts / changes

- `d0751b1` — removed nonexistent PAYEXEC oracle payload copy; next Oracle passed.
- Run `31200979809` (#49) — Oracle=1, NOP=0, LLMaJ PASS; only old evidence-manifest command failed.
- `3a88125` — fixed validation/difficulty evidence manifests and aligned difficulty messaging/`--tests-dir` with per-test policy.
- Run `31201744808` attempt 1 — HTTP 502 during Snorkel login; infrastructure only.
- Run `31201744808` attempt 2 — Oracle=1; NOP Harbor call timed out before execution; infrastructure only.
- Run `31201744808` attempt 3 — refresh limit 20 reached; infrastructure only.

## Do not retry blindly

- Do not call `stb keys refresh` repeatedly on fresh runners after the maximum refresh limit is reached.
- Do not switch CI to the unallocated Edition 3 Portkey project unless account allocation has actually changed.
- Do not modify task logic in response to HTTP 502/read-timeout/refresh-quota failures.
- Do not run difficulty until reusable AI credentials are available, otherwise the five-run suites can be interrupted before producing analyzable trajectories.

## Resume rule

A new chat/controller must first read `.terminus/CONTINUE_SESSION.md`, `.terminus/AGENT_SYSTEM.md`, this checkpoint, the current task files, PR #2, and the latest Actions evidence. Live GitHub/CI evidence overrides stale values in this file; update this checkpoint before making new task changes when they disagree.
