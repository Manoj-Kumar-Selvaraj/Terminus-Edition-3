# Terminus Edition 3 Task Creation Pipeline

Creation policy version: `1.0`

Creation and independent review are separate systems. Before any producer starts, the Creation Controller resolves and pins the current Edition 3 task-rule context for the run. Every creator then uses that `CREATION_RULE_CONTEXT`, this file, `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/agents/QUALITY_AGENT_REGISTRY.md`, and its role prompt. Producers create evidence and artifacts; they do not approve their own work.

## Creation bootstrap / rule resolution

Creation begins with controller-owned rule resolution, not with Scenario Research.

The controller resolves:
- the exact control-plane commit;
- `TERMINUS_3_AI_INSTRUCTIONS.md` as the repository-wide task-rule source;
- `.terminus/reviewers/REVIEWER_CHECKLIST.md`;
- this creation policy;
- `.terminus/agents/PRODUCTION_AUTHENTICITY.md`;
- `.terminus/agents/QUALITY_AGENT_REGISTRY.md`;
- active task-format, complexity, runtime-authenticity, verifier and packaging validators/CI;
- the requested/applicable creation profile and network/environment constraints.

The resolved baseline is handed to creators as `CREATION_RULE_CONTEXT`. If applicable authoritative sources conflict, stop with `POLICY_CONFLICT` before scenario design. If governing task rules materially change during creation, the controller reruns rule resolution and reconciles/invalidate affected producer evidence before continuing.

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
- the creation-rule context is current against governing task rules;
- a **production evidence surface** exists in the solver-visible environment;
- incident claims in `instruction.md` are supported by logs/state/handoff evidence;
- data-backed strict tasks normally start with **10,000–20,000** deterministic, varied primary business records;
- major business modules contain substantive reachable domain logic, not thin business logic hidden behind module/LOC count;
- `.terminus/validate_runtime_authenticity.py <task>` passes.

For COBOL/business-language systems, reject “one IF = one program” construction. Parsing, validation, state classification, multiple business branches and real control-flow paragraphs should be present where the business decision warrants them. Do not pad a trivial comparison with declarations or dead paragraphs merely to satisfy the gate.

## Mandatory producer sequence

### 0. Creation Controller — Rule Resolution
Resolve and pin the authoritative task-rule baseline, active validators, creation profile and environment/network constraints. No producer stage starts until `CREATION_RULE_CONTEXT` is available and any policy conflict is resolved.

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

### 8. Q1 Spec Gap Repairer
Compare legitimate verifier-required behavior with `instruction.md` plus explicitly referenced solver-visible contracts. Close any material verifier->spec gap at the invariant level. Do not copy test names, fixtures, hidden expected values, or assertion ordering into solver-visible prose.

### 9. Q2 Verifier Coverage Repairer
Rebuild the solver-visible requirement list and find any material spec->test gap. Add meaningful behavioral coverage rather than implementation checks or renamed duplicate fixtures. New/changed F2P cases require starter/NOP-fail and Oracle-pass evidence.

### 10. Q3 Spec Ambiguity Repairer
Find competing interpretations that would change grading. Clarify authority, identities, ordering, failure/restart semantics, units, paths, or state transitions only where necessary. Preserve natural handoff style and implementation freedom.

### 11. Documentation Writer
Write reviewer-facing material from evidence. Do not call the environment a benchmark, fixture, cut-down reproduction or package built to demonstrate a bug.

### 12. Q7 Task Format Enforcer
Read the pinned creation-rule context plus current active enforcement/CI before checking exact task structure, `task.toml`, Dockerfiles, verifier image/launcher, solution layout, artifact boundaries, dependency pins, package isolation and forbidden files. Repair deterministic format issues before expensive runtime gates.

### 13. Task Assembly Agent
Run structure/metadata, lint/syntax, `.terminus/validate_task_complexity.py`, `.terminus/validate_runtime_authenticity.py`, Oracle, NOP, F2P/P2P empirical matrix and leakage checks.

### 14. Complexity Governor
Challenge both scale and realism. Ask whether 1,000 lines could disappear without changing the operational system, whether data is meaningfully varied, whether incident evidence is credible, and whether business modules contain actual decision depth.

### 15. Authoring Failure Diagnostician / Q5 Oracle & Runtime Repair Specialist
When deterministic execution fails, preserve the first meaningful failure and classify ownership. Q5 then performs deep repair at the smallest responsible boundary: environment, build, dependency, startup, state, application, Oracle, verifier harness, infrastructure or contract. Never weaken a legitimate test simply to obtain green.

## Frozen candidate quality interlock

After deterministic freeze, run two independent packet-bound reviews before normal Pre-LLMaJ:

### Q4 Spec-Test Contract Reviewer
Independently rebuild both mappings: requirement->test and substantive test behavior->discoverable requirement. It also checks grading-relevant ambiguity and whether gap repairs turned the instruction into a test dump/compressed rubric.

### Q6 Production Logic Auditor
Independently judge whether core solver-visible code/config is reachable, materially diverse, stateful/coupled and credible as production logic. Raw LOC/complexity-validator PASS is not enough; for strict tasks >=3,000 substantive reachable LOC remains required.

`QUALITY_INTERLOCK_PASS` requires Q4 PASS + Q6 PASS, both with sufficient evidence and at least MEDIUM confidence on the exact task commit.

## Pre-model diagnostic simulation

After normal `PRE_LLMAJ: PASS`, run Q8 Model Perspective Difficulty Simulator twice in separate cold executions:
- `GPT_PERSPECTIVE`;
- `CLAUDE_PERSPECTIVE`.

Each perspective receives only solver-visible task evidence before attempting the solve. Do not show either the other result. These runs are diagnostic only, must be labeled simulation, and never replace Harbor LLMaJ or official GPT-5.5 x5 + Claude Opus 4.8 x5 trials.

## Flow

`CREATION_REQUEST -> RULE_RESOLUTION -> IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT(Q1/Q2/Q3) -> DOCUMENTATION_DRAFT -> FORMAT_GATE(Q7) -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION(Q5 on failure) -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK(Q4/Q6) -> PRE_LLMAJ -> Q8 GPT/CLAUDE perspectives -> Harbor/model gates`

## Independence

- Every creator uses the pinned `CREATION_RULE_CONTEXT`; no creator silently substitutes a different repository rule baseline.
- Environment Builder does not build by diffing against the final Oracle.
- Reference Solution Author does not use hidden tests as implementation recipes.
- Verifier Author does not calculate expected values from Oracle source.
- Instruction Writer/Q1 do not use hidden test names, fixture values or private defect IDs as a prose outline.
- Q2 cannot remove a legitimate solver-visible requirement just to simplify the verifier.
- Q3 cannot add implementation requirements that were not part of the operational contract.
- Q4 and Q6 are read-only and cannot approve revisions they authored.
- Q5 cannot weaken legitimate verifier behavior to make Oracle green.
- Q8 simulations cannot see solution/tests/private design before their solve attempt and cannot claim to be official GPT/Claude evidence.
- Creator roles cannot issue the corresponding reviewer PASS.
