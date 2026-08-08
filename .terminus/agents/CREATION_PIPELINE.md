# Terminus Edition 3 Task Creation Pipeline

Creation policy version: `1.0`

This file defines the producer side of the Terminus Edition 3 control plane. Creation and review are separate systems. A creator may produce evidence and artifacts, but it may not approve its own work.

Authoritative Edition 3 rules and the current reviewer checklist override this file when they conflict.

## Large-System Creation Profile

Unless a task is explicitly approved for a smaller profile, new Advanced/Frontier task proposals use the `large_system` profile.

The profile is intentionally demanding, but the numbers are not permission to manufacture clerical complexity.

### Size and topology targets

- Solver-visible implementation/configuration must contain at least **3,000 substantive logical lines** across the environment. Exclude tests, solution files, documentation, comments-only lines, blank lines, generated/vendor output and meaningless repetition.
- Infrastructure tasks should model **30–50 meaningful resources**. A resource counts only when its configuration or relationship can affect observable behavior. Repeated decorative resources do not count.
- Seed **20–30 behavioral defect manifestations** in the starter state.
- At least **10–15 defect manifestations must participate in causal/interdependency edges**. They should arise from a smaller set of operational root causes, not from 20–30 unrelated typos.
- Use **25–30 F2P behavioral verifier cases** for the large-system profile. Every F2P case must fail against the starter/NOP state for a substantive reason and pass against the oracle.
- Add P2P/regression cases where needed to protect behavior that is already correct. P2P quantity follows the task, not a fixed quota.
- Tests are scenarios, not requirements. Several tests may exercise one operational invariant from different states.

### Edition 3 guardrail

The reviewer checklist rejects tasks whose difficulty comes mainly from a large number of independent edge cases or poorly specified requirements. Therefore:

- do not expose the defect inventory in `instruction.md`;
- do not create one prompt sentence per test;
- do not create one isolated bug per test;
- do not inflate line count with dead modules, copy/paste variants or generated filler;
- do not build 30 infrastructure resources if the incident naturally needs 8; reject the idea and select a richer incident instead;
- do not add hidden behavior that a solver cannot discover from the instruction and realistic solver-visible system artifacts.

The objective is a large **system**, not a large **checklist**.

## Creator roles

### 1. Scenario Researcher

Purpose: find a credible engineering incident before implementation begins.

Inputs:
- task domain and requested technologies;
- current Edition 3 rules;
- local task inventory and originality evidence;
- public issue/PR/incident references as calibration only.

Produces:
- 3–5 candidate incidents;
- operational owner/persona;
- affected system boundary;
- why the incident is plausible;
- nearest known benchmark/open-source analogues;
- duplicate/template risk;
- recommendation.

Rules:
- never copy a public issue as the benchmark task;
- prefer failure modes that require reasoning across state/components;
- reject tutorial-style or single-command tasks for the large-system profile;
- identify what an engineer would actually observe before proposing hidden implementation details.

### 2. System Architect / Environment Builder

Purpose: create the realistic solver-visible system and broken initial state.

Owns:
- application/configuration topology;
- Docker environment;
- realistic data/fixtures;
- interfaces and operational artifacts;
- starter code/configuration;
- resource graph for infrastructure tasks.

Large-system obligations:
- >=3,000 substantive solver-visible LOC;
- infrastructure tasks: 30–50 meaningful resources;
- no dead modules or filler to reach the target;
- every major subsystem must be exercised by the normal runtime or documented operational workflow;
- preserve realistic ownership boundaries rather than arranging files around hidden test families.

Must not read the final oracle while constructing the starter state.

### 3. Defect Topology Designer

Purpose: design a coherent network of defects before tests are written.

Produces a private `.terminus/designs/<task>.json` defect graph. This file is never packaged with the task.

Large-system obligations:
- 20–30 defect manifestations;
- 4–8 root-cause clusters is the normal target;
- at least 10–15 manifestations connected by explicit causal edges;
- at least three plausible partial repairs that fix one layer while leaving another wrong;
- defects distributed across components when the scenario warrants it;
- no one-bug-per-test construction.

Each defect entry records:
- stable ID;
- affected component;
- observable failure;
- underlying root cause;
- causal predecessors/dependents;
- why a plausible local fix is incomplete;
- solver-visible evidence that makes diagnosis fair.

### 4. Reference Solution Author

Purpose: independently implement the clean repair from the approved operational contract.

Rules:
- implement a general repair rather than test-specific output;
- deterministic and rerunnable;
- no verifier inspection;
- no hidden special cases for test fixtures;
- handle fresh, partial and repeated execution states where the contract requires them;
- preserve behavior that is not part of the incident;
- minimize unnecessary implementation changes even when the starter codebase is large.

Produces:
- `solution/solve.sh` and private solution assets;
- solution rationale for the controller;
- list of invariants the solution restores.

The Reference Solution Author does not write or approve verifier assertions.

### 5. Verifier Author

Purpose: translate approved solver-visible requirements into behavioral evaluation.

This is a producer role and is distinct from the cold `Verifier Engineer` reviewer.

Method:
1. Build requirement IDs from instruction + legitimate referenced solver-visible artifacts.
2. Define scenario families around operational states, not source files.
3. For large-system tasks create 25–30 F2P cases.
4. Add P2P cases for already-correct behavior that could be broken by a repair.
5. Ensure every F2P case fails on the starter/NOP state and passes on the oracle.
6. Ensure every test has an informative docstring.
7. Prefer running the system and inspecting observable state/artifacts.
8. Avoid source grep/AST implementation enforcement when runtime behavior is observable.
9. Keep tests independent; recreate state per scenario.
10. Keep expected results derived from contracts/invariants rather than reimplementing a complete solver.

Produces a private test classification manifest identifying F2P/P2P cases and requirement mapping.

### 6. Instruction Writer

Purpose: turn the approved incident into the shortest fair human engineering handoff.

The Instruction Writer is intentionally isolated from hidden test details and oracle implementation.

Read:
- incident report;
- solver-visible environment/docs;
- approved operational invariants;
- human-writing calibration corpus.

Do not read:
- hidden test bodies;
- oracle diff;
- defect graph as a sentence checklist.

The instruction should normally contain:
- what is going wrong;
- where it is happening;
- what must be true after the fix;
- only the non-obvious constraints a competent maintainer cannot infer;
- references to realistic existing technical documents when detailed formats live there.

Apply the Jira/Slack handoff and reverse-outline tests. If sentences map neatly to hidden tests, rewrite.

### 7. Documentation Writer

Purpose: create reviewer-facing documentation and metadata explanations from evidence after the task works.

It does not inflate `instruction.md` and does not claim difficulty before trial evidence exists.

### 8. Task Assembly Agent

Purpose: integrate creator outputs into one candidate and run deterministic authoring checks.

Owns:
- task tree assembly;
- metadata completeness;
- code/resource/test count checks;
- task-local lint/syntax checks;
- starter/NOP run;
- oracle run;
- F2P/P2P classification evidence;
- private design manifest consistency.

It must stop and return to the responsible producer when a target can be reached only through filler or hidden requirements.

The Task Assembly Agent cannot mark a task accepted.

### 9. Complexity Governor

Purpose: prevent both under-complex tasks and artificial benchmark construction.

For the `large_system` profile it verifies:
- substantive LOC >= 3,000;
- infra resource count is 30–50 when applicable;
- defect manifestations are 20–30;
- >=10 interrelated manifestations, target 10–15 or more;
- F2P count is 25–30;
- P2P cases exist where preserving existing behavior matters;
- no obvious filler/dead-code inflation;
- defect graph has fewer root-cause clusters than manifestations;
- prompt does not enumerate defect/test inventory;
- task remains interesting and well specified under Edition 3.

If numeric targets conflict with natural scope, the governor must reject the candidate scenario rather than pad it.

## Creation flow

`IDEA -> SCENARIO_RESEARCH -> ARCHITECTURE -> DEFECT_GRAPH -> STARTER_BUILD -> ORACLE_AUTHORING -> VERIFIER_AUTHORING -> INSTRUCTION_WRITING -> ASSEMBLY -> COMPLEXITY_GATE -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE`

Only after `FROZEN_CANDIDATE` does the independent review system begin:

`Task Architect review -> Verifier Engineer -> Compliance -> Originality -> Instruction Reviewer -> Documentation Reviewer -> Comprehensive Reviewer -> Pre-LLMaJ -> Harbor LLMaJ -> difficulty trials`

## Independence matrix

| Producer | Must not self-approve through |
| --- | --- |
| Scenario Researcher | Originality & Authenticity Reviewer |
| Environment Builder | Task Architect / Compliance Auditor |
| Defect Topology Designer | Difficulty Reviewer |
| Reference Solution Author | Verifier Engineer |
| Verifier Author | Verifier Engineer / Comprehensive Reviewer |
| Instruction Writer | Instruction Reviewer / Human Quality Reviewer |
| Documentation Writer | Engineering Documentation Reviewer |
| Task Assembly Agent | Comprehensive Reviewer |
| Complexity Governor | Difficulty Reviewer / Originality Reviewer |

## Required private creator artifacts

Store outside the task directory:

- `.terminus/designs/<task>.json` — scenario, resource metrics, defect graph and causal edges;
- `.terminus/designs/<task>-test-map.json` — requirement/F2P/P2P mapping;
- `.terminus/research/<task>.md` — originality/provenance research notes;
- `.terminus/reviews/...` — independent reviewer reports.

These files are controller evidence and must not be copied into the submitted task package or task environment.
