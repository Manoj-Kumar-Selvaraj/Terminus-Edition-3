# Terminus Edition 3 Task Creation Pipeline

Creation policy version: `1.0`

Creation and independent review are separate systems. Every creator reads the current Edition 3 rules, this file, `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, and its role prompt. Producers create evidence and artifacts; they do not approve their own work.

## Default strict profile

Advanced/Frontier operational tasks use `large_system_strict` unless the controller records why a smaller task is inherently more realistic.

Hard authoring constraints:
- at least **3,000** substantive solver-visible runtime/configuration lines;
- infrastructure tasks: **30–50** meaningful interacting resources;
- **20–30** defect manifestations from materially fewer root causes;
- at least 15 manifestations connected through causal/interdependency edges;
- **25–30** non-duplicative F2P behavioral tests;
- P2P coverage where already-correct behavior can regress.

Numbers never waive authenticity. If the incident needs filler to hit the profile, return `SCENARIO_TOO_SMALL`.

## Production-authenticity gate

Operational/stateful tasks must also satisfy `.terminus/agents/PRODUCTION_AUTHENTICITY.md`.

Before `FROZEN_CANDIDATE`:
- a **production evidence surface** exists in the solver-visible environment;
- incident claims in `instruction.md` are supported by logs/state/handoff evidence;
- data-backed strict tasks normally start with **10,000–20,000** deterministic, varied primary business records;
- major business modules contain substantive reachable domain logic, not thin business logic hidden behind module/LOC count;
- `.terminus/validate_runtime_authenticity.py <task>` passes.

For COBOL/business-language systems, reject “one IF = one program” construction. Parsing, validation, state classification, multiple business branches and real control-flow paragraphs should be present where the business decision warrants them. Do not pad a trivial comparison with declarations or dead paragraphs merely to satisfy the gate.

## Mandatory producer sequence

### 1. Scenario Researcher
Produce 3–5 credible incidents, operational persona, observed failure, durable state, evidence that would realistically exist, originality references, and scale fit. A production incident without plausible evidence artifacts is rejected.

### 2. System Architect / Environment Builder
Build the runtime topology, state, configuration, logs/operator artifacts and broken starter. All counted modules/resources must be reachable. For data-backed strict tasks, build representative deterministic history/state rather than toy fixtures.

### 3. Defect Topology Designer
Design 4–8 root-cause clusters and 20–30 manifestations with cross-cluster edges and plausible partial-fix traps. Do not create one independent bug per test.

### 4. Reference Solution Author
Repair the approved operational invariants without reading hidden verifier bodies before the first oracle implementation is frozen. No fixture/test special casing.

### 5. Verifier Author
Build behavioral tests from solver-visible requirements/contracts. Strict profile uses 25–30 F2P cases and P2P as needed. Every F2P must empirically starter/NOP-fail and Oracle-pass.

### 6. Human Writing Researcher
Use real public engineering issue/incident/ticket sources as information-selection calibration. Apply the incident evidence test before drafting: every asserted production event must be supported by a solver-visible artifact or be removed.

### 7. Instruction Writer
Write the shortest fair engineer handoff. Point to logs/state/runbooks instead of narrating the hidden test inventory. Do not invent backstory to manufacture realism. Apply Jira/Slack handoff, reverse-outline and incident-evidence checks.

### 8. Documentation Writer
Write reviewer-facing material from evidence. Do not call the environment a benchmark, fixture, cut-down reproduction or package built to demonstrate a bug.

### 9. Task Assembly Agent
Run structure/metadata, lint/syntax, `.terminus/validate_task_complexity.py`, `.terminus/validate_runtime_authenticity.py`, Oracle, NOP, F2P/P2P empirical matrix and leakage checks.

### 10. Complexity Governor
Challenge both scale and realism. Ask whether 1,000 lines could disappear without changing the operational system, whether data is meaningfully varied, whether incident evidence is credible, and whether business modules contain actual decision depth.

### 11. Authoring Failure Diagnostician
Classify Oracle/NOP failures to the smallest responsible layer. Do not weaken valid tests merely to get green.

## Flow

`IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> DOCUMENTATION_DRAFT -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE`

Only then begin independent Task Architect / Verifier / Compliance / Originality / writing / Comprehensive / Pre-LLMaJ review.

## Independence

- Environment Builder does not build by diffing against the final Oracle.
- Reference Solution Author does not use hidden tests as implementation recipes.
- Verifier Author does not calculate expected values from Oracle source.
- Instruction Writer does not see hidden test names or private defect IDs as a prose outline.
- Creator roles cannot issue the corresponding reviewer PASS.
