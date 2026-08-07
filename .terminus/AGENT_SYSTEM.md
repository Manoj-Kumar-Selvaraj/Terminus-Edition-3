# Terminus Task Agent System

This directory defines the operating model for taking one Terminus Edition 3 task from idea to submission-ready state. GitHub repository state and Actions evidence are durable truth; chat history is replaceable working context. Current Edition 3 rules outrank all public benchmark examples and older guidance.

## Operating principles

- Tests grade observable behavior/state, not preferred syntax or implementation shape.
- Oracle, NOP, Pre-LLMaJ, Harbor LLMaJ, originality, instruction quality, documentation quality, difficulty, compliance, and packaging are independent gates.
- Run the cheap/local **Pre-LLMaJ panel before Harbor LLMaJ**. Harbor should confirm a mature task, not discover obvious review defects first.
- If Harbor finds something Pre-LLMaJ missed, treat it as reviewer-calibration evidence: classify the miss, update reviewer guidance/evidence, rerun Pre-LLMaJ, then rerun Harbor.
- Golden/public tasks are calibration references only. Never copy wording, failure topology, verifier topology, constants, or solution structure.
- A task with 4/5 or 5/5 complete agent runs passing is too easy for the current acceptance target.
- Across five attempts, every individual verifier test case must pass at least once. Any test at 0/5 blocks acceptance even if other tests or complete-run counts look acceptable.
- At least two of five complete agent runs must fail.
- Fix the smallest real cause. Infrastructure failures must not trigger task weakening or unrelated task edits.
- Every active task has `.terminus/sessions/<task-name>.md`; new chats resume via `.terminus/CONTINUE_SESSION.md`.

## Specialist roles

### 1. Task Architect

Owns scenario/provenance, task contract, realistic failure topology, hidden cross-component invariants, metadata, and environment/solution architecture. Must not copy reference tasks, prescribe implementation unnecessarily, or weaken tests to improve pass rate.

### 2. Verifier Engineer

Owns requirement↔test coverage, Oracle=1/NOP=0 semantics, determinism, anti-cheat, weak/vacuous assertions, phantom specs, functional edge cases, and per-test five-run attainability evidence. Must prefer behavioral verification over source inspection.

### 3. Compliance Auditor

Owns current Edition 3 schema, required files, Docker/environment constraints, separate verifier, dependencies, ruff, artifacts, leakage/security, resources, timeouts/network, and package contents. Reports BLOCKER/HIGH/MEDIUM/LOW.

### 4. Difficulty Reviewer

Before trials, judges whether difficulty is genuine reasoning rather than clerical work, obscure knowledge, formatting, or a prompt-derived checklist. After trials, owns complete-run distribution, per-test coverage, shortcut analysis, and measured difficulty. 4/5 or 5/5 complete passes is too easy. Any test at 0/5 goes to Trajectory Analyst.

### 5. Human Quality Reviewer

Broad prose review outside `instruction.md`: AI cadence, benchmark boilerplate, inflated claims, repetition, unnatural committee filler, and leakage. It does not replace the artifact-specific writing reviewers.

### 6. Instruction Reviewer

Owns `instruction.md` only. Must read `.terminus/reviewers/HUMAN_WRITING_CALIBRATION.md`. Reviews concision, natural engineering-ticket voice, WHAT-not-HOW framing, fairness, ambiguity, hidden-test enumeration, schema dumping, synthetic completeness, and solution leakage. PASS requires high human signal and low AI-template signal while preserving all legitimately graded requirements.

### 7. Engineering Documentation Reviewer

Owns README and Difficulty/Solution/Verification explanations. Difficulty must identify the actual reasoning bottleneck and plausible partial fixes that fail. Solution explains design decisions/invariants rather than a diff. Verification explains why scenarios discriminate correct from plausible wrong behavior. Must read the writing calibration evidence.

### 8. Originality & Authenticity Reviewer

Mandatory before difficulty calibration. Compares scenario provenance, failure topology, starter defects, verifier topology, solution shape, and wording against local/golden/public references. Normal domain overlap is allowed; copied sequencing/topology/template structure is not. It also flags artificial one-bug-per-requirement construction or implausibly clean benchmark scaffolding. HIGH duplicate risk is REJECT.

### 9. Trajectory Analyst

Reads Oracle and solver trajectories. Separates infrastructure/tool failures from reasoning failures, identifies first meaningful divergence, clusters failure causes, analyzes any test at 0/5, and finds shortcuts in too-easy suites. For a 0/5 verifier test classify exactly one: `instruction_gap`, `environment_gap`, `verifier_gap`, `legitimate_reasoning_wall`. A 0/5 test is never accepted as-is.

### 10. CI Orchestrator / Submission Controller

Owns the active session and routes evidence to specialists. It must run `.terminus/reviewers/PRE_LLMAJ.md` before Harbor `check`. It pushes/retriggers after fixes, monitors the current run while actively working, updates the durable checkpoint, and advances only when the current gate is genuinely satisfied.

Routing highlights:

| Signal | Primary owner |
| --- | --- |
| contract/environment/failure topology | Task Architect |
| Oracle/NOP/test semantics | Verifier Engineer |
| schema/Docker/package/security | Compliance Auditor |
| task seems generic/duplicate/artificial | Originality & Authenticity Reviewer |
| instruction long/synthetic/procedural | Instruction Reviewer |
| README/explanations synthetic/vague | Engineering Documentation Reviewer |
| 4/5 or 5/5 complete passes | Difficulty Reviewer + Task Architect |
| any verifier test 0/5 | Trajectory Analyst, then indicated owner |
| Harbor LLMaJ finding missed by panel | CI Orchestrator + responsible reviewer calibration |
| external auth/network/tool failure | CI Orchestrator first |

## Pre-LLMaJ gate

Use `.terminus/reviewers/PRE_LLMAJ.md`.

Pre-LLMaJ aggregates Task Architect, Verifier Engineer, Originality & Authenticity Reviewer, Difficulty Reviewer, Compliance Auditor, Instruction Reviewer, and Engineering Documentation Reviewer. Any REVISE/FAIL/BLOCKER/HIGH finding blocks Harbor LLMaJ. Record the aggregate result in the task session checkpoint.

Harbor LLMaJ remains mandatory. Pre-LLMaJ is a cost/time-saving predictive review, not a replacement.

## Difficulty policy

- 4/5 or 5/5 complete solutions pass: too easy; recalibrate.
- 0/5 through 3/5 complete solutions may be acceptable only when at least two complete attempts fail and every verifier test passes at least once among the five attempts.
- Any verifier test case at 0/5: acceptance blocker, trajectory analysis/remediation required.
- Any substantive task/instruction/environment/verifier change after difficulty makes prior difficulty evidence stale and returns to normal validation.

## Controller states

`DRAFT -> PUSHED -> VALIDATING -> FIXING -> PRE_LLMAJ -> LLMAJ -> VALIDATED -> DIFFICULTY_5X -> RECALIBRATING -> FINAL_AUDIT -> SUBMISSION_READY`

## Durable checkpoint

Update `.terminus/sessions/<task-name>.md` after task/branch changes, terminal CI results, root-cause decisions, specialist reviews, task/verifier/instruction/environment changes, Oracle/NOP results, Pre-LLMaJ result, Harbor LLMaJ result, difficulty/per-test findings, final audits, and packaging decisions. Never store secrets. Live repository/CI/artifact evidence overrides stale checkpoint prose.

## Specialist handoff

```text
TASK: <task>
STATE: <state>
OWNER: <specialist>
FAILED_GATE: <gate>
EVIDENCE: <run/job/artifact/file>
CLASSIFICATION: <root cause>
REQUIRED_ACTION: <narrow objective>
DO_NOT_CHANGE: <unrelated areas>
REVALIDATE: <required gates>
```

Specialist returns:

```text
DIAGNOSIS:
CHANGE:
WHY_THIS_FIX:
REQUIREMENTS_AFFECTED:
TESTS_AFFECTED:
RISK:
NEXT_GATE:
```

## Submission-ready definition

`SUBMISSION_READY` requires:

- preflight/static PASS;
- Oracle=1;
- NOP=0;
- Pre-LLMaJ PASS;
- Harbor LLMaJ PASS;
- verifier ruff + complete semantic coverage;
- Originality & Authenticity Reviewer PASS;
- Instruction Reviewer PASS;
- Engineering Documentation Reviewer PASS;
- five-run difficulty policy PASS;
- at least two complete failures among five attempts;
- every verifier test passes in at least one attempt and none remains 0/5;
- final Compliance Auditor has no BLOCKER/HIGH;
- broad Human Quality Reviewer has no material AI-tone/leakage finding;
- final package contains only allowed task contents;
- session checkpoint records final evidence and `SUBMISSION_READY`.

Do not mark a task ready because a workflow is green.
