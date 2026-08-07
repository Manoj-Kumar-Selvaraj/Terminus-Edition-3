# Terminus Task Session

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `VALIDATING`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Last checkpoint task commit: `38eb445e976be327a8fb2064ff896df24a85cd7d`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PASS | run 31200979809 (#49); no structural verifier change since |
| Ruff verifier | PASS | run 31200979809 (#49); verifier unchanged |
| STB auth/AI credentials | BLOCKED | active Edition-2 Portkey project/account reached maximum refresh limit 20 |
| Oracle = 1 | PASS | run 31200979809 (#49); oracle/verifier behavior unchanged by instruction-only rewrite |
| NOP = 0 | PASS | run 31200979809 (#49); starter/verifier behavior unchanged by instruction-only rewrite |
| LLMaJ | STALE | instruction.md changed in 38eb445; rerun required when reusable AI credentials are available |
| Evidence manifest | PASS | fixed workflow; later validation attempts prove manifest step succeeds |
| Difficulty 5x | NOT_RUN | blocked until reusable AI credentials avoid fresh refresh consumption |
| Per-test 1/5 minimum | NOT_RUN | difficulty not run |
| Instruction Reviewer | PENDING | new dedicated final gate; current instruction rewritten to ~126 words but must receive an independent final PASS |
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

Instruction revision:
- `38eb445e976be327a8fb2064ff896df24a85cd7d` rewrote `instruction.md` from a dense schema-heavy specification into a concise two-paragraph incident ticket (~126 words).
- The business behavior was not intentionally changed; output schemas and detailed business invariants remain in the supplied `/app/eod/contracts/eod_contract.md` referenced by the instruction.
- Because instruction.md changed, LLMaJ and final text-quality review are stale/pending even though Oracle/NOP behavior evidence remains valid.

CI clarity change:
- `896eefc51b8e9b79d0ce50c1957307837f42de95` added `paths-ignore: .terminus/**` for pushes to main, so checkpoint-only controller updates no longer create misleading all-skipped green validation runs.

Later infrastructure-only failures:
- Run `31201744808` attempt 1: Snorkel `/users/me` returned HTTP 502 before task execution.
- Run `31201744808` attempt 2: Oracle PASS; NOP Harbor call failed before trial execution with `The read operation timed out`.
- Run `31201744808` attempt 3: STB login PASS; Portkey refresh failed with `Maximum refresh limit (20) reached` before task execution.

## Current blocker

Fresh GitHub-hosted runners currently require `stb keys refresh`, and the active Edition-2 Portkey project/account has reached its maximum refresh count. Do not burn further runs by repeatedly refreshing credentials. The next infrastructure objective is reusable model credentials injected securely from GitHub Secrets (or another approved durable mechanism) without generating a new Portkey key on every runner.

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `ci_infrastructure`
- Evidence: run `31201744808` attempt 3 shows `Maximum refresh limit (20) reached` in `Authenticate stb and refresh AI credentials`.
- Task edits required for credential failure: `none`.

## Task fixes already completed

1. Environment Dockerfile creates `/app/eod/state` before initializing SQLite.
2. Oracle solution paths use Harbor's `/solution` mount instead of `/oracle`.
3. Removed nonexistent `/solution/correct/payexec.cob` copy; starter PAYEXEC satisfies its direct interface tests.
4. Oracle copies corrected `paydup.cob`, `schema.sql`, and `run_eod.sh`, rebuilds sample state, and executes the corrected EOD flow.
5. Evidence-manifest shell enumeration was fixed and difficulty CI aligned with the per-test 0/5 policy.
6. `instruction.md` was rewritten to a concise two-paragraph incident ticket (~126 words).
7. Dedicated Instruction Reviewer was added as a mandatory final submission gate.
8. `.terminus/**`-only pushes no longer trigger task validation on main.

## Next action

Implement a secure reusable-AI-credential path for CI so fresh runners do not consume another Portkey refresh. Then rerun LLMaJ/normal validation for the revised instruction, execute five-trial difficulty calibration, analyze complete-run and per-test coverage, and run the dedicated Instruction Reviewer before final compliance/human-quality/package gates.

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
- Any verifier test case at 0/5 is an acceptance blocker; analyze trajectories and repair the task/instruction/environment/verifier until no test remains 0/5.

## Instruction review checkpoint

- Verdict: `PENDING`
- Word count: `~126`
- Material requirements preserved: `intended yes; final dedicated review must verify against contract + verifier`
- Evidence/review: `instruction revision commit 38eb445; final Instruction Reviewer not yet run`

Any later instruction.md change makes this gate STALE until the dedicated Instruction Reviewer runs again.

## Decisions that must survive chat changes

- Use current Terminus Edition 3 rule files and `.terminus/AGENT_SYSTEM.md` as authoritative local tasking guidance.
- Use the eight-role agent system: Task Architect, Verifier Engineer, Compliance Auditor, Difficulty Reviewer, Human Quality Reviewer, Instruction Reviewer, Trajectory Analyst, CI Orchestrator / Submission Controller.
- Instruction Reviewer is independent and mandatory at final submission even when Human Quality Reviewer passes.
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

- `38eb445` — rewrote instruction.md to ~126 words, two concise incident-focused paragraphs; final Instruction Reviewer pending.
- `896eefc` — checkpoint-only `.terminus/**` pushes no longer trigger main task-validation workflow.
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
- Do not run difficulty until reusable AI credentials are available, otherwise five-run suites can be interrupted before producing analyzable trajectories.
- Do not mark submission ready without a final dedicated Instruction Reviewer PASS.

## Resume rule

A new chat/controller must first read `.terminus/CONTINUE_SESSION.md`, `.terminus/AGENT_SYSTEM.md`, this checkpoint, the current task files, PR #2, and the latest Actions evidence. Live GitHub/CI evidence overrides stale values in this file; update this checkpoint before making new task changes when they disagree.
