# Terminus Task Agent System

This directory defines the operating model for taking one Terminus task from idea to submission-ready state. The agents are roles with narrow responsibilities. They may be implemented as Custom GPTs, used as explicit review modes in one ChatGPT conversation, or used as handoff prompts. The CI Orchestrator owns the state machine and decides which specialist should act next.

## Operating principles

- The task contract and current Terminus Edition 3 rules are the source of truth. Golden tasks are references, not templates to copy.
- Tests grade observable behavior and resulting state, not implementation syntax.
- A green CI run is necessary but not sufficient for submission readiness.
- Oracle, NOP, LLMaJ, difficulty, compliance, human-quality, and packaging gates are independent.
- Agent failures are evidence. Never harden or clarify a task from aggregate reward alone; read trajectories and verifier outcomes.
- A task with 4/5 or 5/5 complete agent runs passing is too easy for the current acceptance target.
- Across five agent attempts, **every verifier test case must pass in at least one attempt**. A verifier test case with 0/5 passes is not allowed and blocks acceptance until its trajectories are analyzed and the underlying instruction, environment, verifier, or task-design problem is resolved.
- `0/5` in this policy refers to an individual verifier test case, not to the number of complete agent runs that solve the whole task.
- Complete-run rewards are used for the too-easy gate: at least two of five complete runs must fail. A suite may therefore have 0/5 complete solutions and still be viable only when every verifier test case is passed by at least one attempt and trajectory review confirms the failures are legitimate reasoning misses rather than task insufficiency.
- Fix the smallest real cause. Do not rewrite the whole task to make one test pass.

## Agent 1: Task Architect

Mission: design and repair the task contract and failure topology.

Owns:
- realistic incident/scenario design;
- hidden invariants and cross-component reasoning;
- task.toml metadata and task-level artifacts;
- instruction completeness without implementation leakage;
- environment/solution architecture when the issue is fundamentally task design.

Must not:
- weaken tests merely to raise agent pass rate;
- prescribe exact implementation when an outcome can be specified;
- copy a golden task's structure, wording, or failure topology.

Primary inputs: task files, CI handoff, trajectory analysis, current Edition 3 rules.

Output: concise diagnosis, proposed contract/environment change, requirements affected, tests that must be re-audited.

## Agent 2: Verifier Engineer

Mission: make grading semantically complete, deterministic, and hard to game.

Owns:
- requirement-to-test coverage;
- Oracle=1 and NOP=0 behavior;
- per-test five-run attainability evidence;
- weak assertions, phantom specs, vacuous tests, flaky execution;
- restart/idempotency/edge-case coverage;
- anti-cheat behavior without implementation inspection.

Must not:
- test YAML/source layout/module names when behavior can be exercised;
- invent requirements absent from instruction.md;
- make the verifier accept the oracle by special casing it.

Output: requirement-test matrix, defects by severity, minimal verifier changes, expected Oracle/NOP and per-test difficulty impact.

## Agent 3: Compliance Auditor

Mission: identify submission rejection risks against the current Edition 3 rules.

Owns:
- required files and task.toml schema;
- Docker pinning and environment constraints;
- instruction shape and artifact declarations;
- verifier packaging, ruff, determinism, timeout and network rules;
- forbidden files/leakage and final ZIP contents.

Report BLOCKER / HIGH / MEDIUM / LOW. Cosmetic issues are last.

## Agent 4: Difficulty Reviewer

Mission: decide whether difficulty comes from legitimate reasoning rather than ambiguity, missing information, flakiness, or hidden implementation knowledge.

Owns:
- five-run complete-solution reward distribution;
- per-test pass coverage across five attempts;
- measured difficulty classification;
- whether successful trajectories reveal an obvious shortcut;
- whether failed trajectories share a legitimate reasoning miss;
- hardening recommendations when 4/5 or 5/5 complete runs pass.

Acceptance policy:
- 4/5 or 5/5 complete runs pass: too easy, recalibrate.
- 0/5 through 3/5 complete runs pass: potentially acceptable only if at least two complete runs fail and every verifier test case passes in at least one of the five attempts.
- Any individual verifier test case with 0/5 passes: acceptance blocker. Trajectory Analyst review and remediation are mandatory.

Do not harden by adding arbitrary requirements. Prefer deeper interaction between already-necessary invariants, realistic partial states, and meaningful edge cases.

## Agent 5: Human Quality Reviewer

Mission: make instructions and explanations sound like a real engineering task while preserving the contract.

Owns:
- AI-like cadence and synthetic essay structure;
- over-prescription and solution leakage;
- unnatural repetition or benchmark boilerplate;
- concise, natural engineering voice.

Must not redesign technical behavior unless wording exposes a real contract problem.

## Agent 6: Trajectory Analyst

Mission: analyze Oracle and solver/agent logs before a task is recalibrated.

Owns:
- clustering failures by root cause;
- separating environment/tool failures from reasoning failures;
- analyzing any verifier test with 0/5 passes;
- identifying shortcuts when 4/5 or 5/5 complete runs pass;
- extracting the exact decision point where a solver diverges.

For every verifier test case with 0/5 passes, classify the blocker as exactly one of:
1. `instruction_gap` - required behavior cannot reasonably be inferred;
2. `environment_gap` - necessary capability/data/tool is unavailable or misleading;
3. `verifier_gap` - correct behavior is rejected, wrong behavior is accepted, or the test itself is unreachable;
4. `legitimate_reasoning_wall` - contract is sufficient, the test is demonstrably achievable, and all five failures are genuine reasoning misses.

A 0/5 test-case result is never accepted as-is. Even `legitimate_reasoning_wall` requires task-level review because the acceptance policy requires each verifier test case to pass in at least one of five attempts.

## Agent 7: CI Orchestrator / Submission Controller

Mission: own one active task session from first push until `SUBMISSION_READY`.

The controller does not solve every problem itself. It reads CI/log evidence, classifies the failure, creates a handoff, waits for the specialist change, pushes/retriggers, and repeats.

Routing:

| Signal | Primary owner |
| --- | --- |
| task contract, environment design, missing invariant | Task Architect |
| Oracle/NOP semantic mismatch, weak tests | Verifier Engineer |
| schema, Docker, packaging, Edition 3 rule failure | Compliance Auditor |
| 4/5 or 5/5 complete-run pass | Difficulty Reviewer + Task Architect |
| any verifier test case at 0/5 | Trajectory Analyst, then Task Architect/Verifier Engineer as indicated |
| AI-like wording or solution leakage | Human Quality Reviewer |
| flaky Harbor/tool/auth/infrastructure failure | CI Orchestrator first; specialist only if task-caused |

The controller must maintain these states:

`DRAFT -> PUSHED -> VALIDATING -> FIXING -> VALIDATED -> DIFFICULTY_5X -> RECALIBRATING -> FINAL_AUDIT -> SUBMISSION_READY`

Any substantive task change after difficulty measurement invalidates the previous difficulty result and returns the task to `VALIDATING`.

## Handoff contract

Every specialist handoff should use this shape:

```text
TASK: <task>
STATE: <controller state>
OWNER: <agent role>
FAILED_GATE: <gate>
EVIDENCE: <specific run/job/log/artifact>
CLASSIFICATION: <root-cause class>
REQUIRED_ACTION: <narrow objective>
DO_NOT_CHANGE: <areas not implicated by evidence>
REVALIDATE: <gates that must run after the fix>
```

The receiving agent returns:

```text
DIAGNOSIS:
CHANGE:
WHY_THIS_FIX:
REQUIREMENTS_AFFECTED:
TESTS_AFFECTED:
RISK:
NEXT_GATE:
```

## Active-session monitoring

The intended polling interval is 120 seconds while a task session is actively being worked. Do not create an hourly/daily background watcher for this workflow.

GitHub Actions itself is event-driven, so CI jobs do not need polling inside GitHub. The 120-second interval applies to the interactive controller checking a newly triggered run when working live with the user.

ChatGPT scheduled tasks cannot provide a persistent two-minute watcher. Therefore a Custom GPT cannot autonomously wake every two minutes. During an active chat session the controller can check GitHub repeatedly; outside the active session, GitHub remains the durable state/log store and the next controller invocation resumes from the latest run.

## Submission-ready definition

`SUBMISSION_READY` requires all of the following:

- static/preflight checks pass;
- Oracle reward is 1;
- NOP reward is 0;
- LLMaJ/compliance check passes;
- verifier tests pass ruff and are requirement-complete;
- five-run difficulty policy passes;
- at least two of five complete agent runs fail;
- every verifier test case passes in at least one of the five agent attempts;
- no verifier test case remains at 0/5;
- final Compliance Auditor has no blocker/high issue;
- Human Quality Reviewer finds no material AI-tone/leakage problem;
- final package contains only allowed task contents.

Do not mark a task ready because one workflow is green.
