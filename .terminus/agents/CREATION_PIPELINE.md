# Terminus Edition 3 Task Creation Pipeline

Creation policy version: `1.1`

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

For `large_system_strict`, the default task shape is a **substantial production engineering work package**, not a single localized bug report. Suitable work packages include feature/reliability completion, migration completion, recovery implementation, platform modernization, operability completion, security hardening, state-model rework, integration completion, or incident-driven remediation whose required end state spans multiple coupled subsystems/invariants. An incident may explain why the work exists, but it should not be the sole source of difficulty.

Hard authoring constraints are minimum floors/ranges, not quotas or preferred target sizes:
- **at least 3,000 substantive, reachable solver-visible runtime/configuration LOC, with no upper target**; a naturally coherent system may be 5,000, 10,000 or more lines when its domain/architecture requires them;
- counted LOC must be meaningful production/domain implementation, not duplicated, generated/vendor, dead/unreachable, boilerplate-only, unnecessary or micro-module-inflated code;
- the solver-visible system must exhibit production characteristics appropriate to the domain: differentiated module responsibilities, real runtime/operator entrypoints, realistic state/data, validation/error handling, configuration, operational workflows, meaningful coupling, and persistence/restart/recovery/idempotency/failure behavior where applicable;
- infrastructure tasks: **30–50** meaningful interacting resources where that scale is natural; decorative copies do not count;
- **20–30** defect manifestations from materially fewer root causes;
- at least 15 manifestations connected through meaningful causal/interdependency edges;
- **25–30 non-duplicative F2P behavioral tests derived organically** from distinct operational requirements, states, transitions, failure modes and interactions;
- P2P coverage where already-correct behavior can realistically regress;
- sufficient domain-relevant edge, boundary, negative and failure-path coverage according to operational risk.

Negative/failure-path cases are not a third taxonomy: classify them F2P or P2P according to whether the starter behavior must change or be preserved. Do not manufacture edge cases by simply varying fixture values; they must exercise materially different boundaries, invariants, rejection/safety semantics, recovery behavior or operational transitions.

Numbers never waive authenticity. If the engineering work package needs filler, unrelated requirements, duplicate code/resources, artificial tests or invented edge cases to hit the profile, return `SCENARIO_TOO_SMALL`.

## Production-authenticity gate

Operational/stateful tasks must also satisfy `.terminus/agents/PRODUCTION_AUTHENTICITY.md`.

Before `FROZEN_CANDIDATE`:
- the creation-rule context is current against governing task rules;
- a **production evidence surface** exists in the solver-visible environment when the work package asserts inherited operational/current-state facts;
- current-state claims in `instruction.md` are supported by logs/state/handoff evidence; desired functional requirements do not need to be disguised as incident evidence;
- data-backed strict tasks normally start with **10,000–20,000** deterministic, varied primary business records;
- major business modules contain substantive reachable domain logic, not thin business logic hidden behind module/LOC count;
- module/resource/test scale is structurally necessary rather than quota-driven;
- normal, edge, boundary, negative and failure-path behavior is sufficiently represented for the claimed operational system;
- `.terminus/validate_runtime_authenticity.py <task>` passes.

For COBOL/business-language systems, reject “one IF = one program” construction. Parsing, validation, state classification, multiple business branches and real control-flow paragraphs should be present where the business decision warrants them. Do not pad a trivial comparison with declarations or dead paragraphs merely to satisfy the gate.

## Instruction / documentation boundary

Edition 3 allows `instruction.md` to be concise as **<=2 short paragraphs or <=20 bullets**. For large strict tasks, up to 20 concise bullets is acceptable when needed to state the complete material work package.

`instruction.md` owns:
- the engineering objective/change request;
- the material functional and operational requirements needed for a fair solve;
- important preservation, compatibility and safety requirements;
- required output/artifact paths and exact structured-output schema where the governing Edition 3 rules require them;
- concise references to solver-visible technical documentation.

Solver-visible environment documentation may own normal engineering detail such as:
- repository/folder/component layout;
- runtime/operator entrypoints;
- architecture and state-model descriptions;
- schemas, record layouts and protocol semantics;
- API/CLI/operator contracts and runbooks.

Do not move the actual task goal or material functional requirements into docs merely to bypass the instruction length limit. Conversely, do not bloat `instruction.md` with folder-by-folder explanations or implementation diagnosis that belongs in normal technical documentation or code inspection.

The desired separation is: **instruction = what must work; docs/contracts = how the inherited system is organized and governed; code/runtime state = what is currently implemented; solver = determine the implementation gaps and repair them.**

## Mandatory producer sequence

### 0. Creation Controller — Rule Resolution
Resolve and pin the authoritative task-rule baseline, active validators, creation profile and environment/network constraints. No producer stage starts until `CREATION_RULE_CONTEXT` is available and any policy conflict is resolved.

### 1. Scenario Researcher
Produce 3–5 credible **engineering work-package** candidates, not merely isolated incidents. For each candidate define the engineering objective, operational persona, required end state, major coupled requirement families, inherited system/state that makes the work meaningful, originality references, and scale fit. An incident/change history may provide context, but strict difficulty should come from completing or repairing a substantial coupled work package. Confirm the candidate can naturally support a substantive production codebase above the 3,000-LOC floor, organic F2P diversity, and realistic normal/edge/failure behavior without unrelated requirements or filler.

### 2A. System Architect — clean architecture design
Design only the inherited production system shape before any private defect/incomplete-behavior topology exists. Produce the component/resource graph, runtime/operator entrypoints, state/persistence model, solver-visible technical-documentation plan, production characteristics, scale fit and reachability plan. **Do not create the broken starter and do not inject defects at this stage.** The output is the clean architecture contract consumed by A3.

### 3. Defect Topology Designer
Against the approved clean architecture, design 4–8 root-cause clusters and 20–30 manifestations with at least 15 manifestations participating in meaningful causal/interdependency edges, plus cross-component/cross-cluster relationships and plausible partial-fix traps. Build a `behavioral_surfaces` map spanning normal operation and domain-relevant edge/boundary, negative/rejection, failure/recovery and cross-component behavior so later F2P coverage can arise organically. Do not create one independent bug per test or manufacture manifestations merely to satisfy counts; return `SCENARIO_TOO_SMALL` when the work package cannot naturally support the strict causal and behavioral breadth.

### 2B. Environment Builder — starter materialization
Re-invoke A2 only after the A3 topology is approved. Materialize the solver-visible runtime, state, configuration, technical docs, logs/operator artifacts where appropriate, and broken/incomplete starter from **both** the clean architecture and approved defect topology. All counted modules/resources must be reachable. For data-backed strict tasks, build representative deterministic history/state rather than toy fixtures. Inject only approved defect/incomplete behaviors; do not add untracked surprise bugs. Technical docs should explain structure/contracts naturally without diagnosing which implementation pieces the solver must change.

### 4. Reference Solution Author
Repair/complete the approved operational invariants without reading hidden verifier bodies before the first oracle implementation is frozen. No fixture/test special casing.

### 5. Verifier Author
Build behavioral tests from solver-visible requirements/contracts. Strict profile uses 25–30 F2P cases **only when they arise organically from materially distinct operational behavior**; the range is not a quota. Add P2P according to actual preservation risk. Include sufficient positive, edge, boundary, negative and failure-path scenarios for the domain. Negative cases remain F2P or P2P according to their starter-to-Oracle transition. Every F2P must empirically starter/NOP-fail and Oracle-pass.

### 6. Human Writing Researcher
Use real public Jira/issues/change requests/engineering tickets and incident handoffs as information-selection calibration. Distinguish **required end-state behavior** from **asserted current-state facts**. Current-state facts included in the handoff must be supported by solver-visible evidence; do not invent implementation diagnoses or fake operational backstory merely to make the task sound realistic.

### 7. Instruction Writer
Write a concise engineering handoff using the Edition 3 limit: <=2 short paragraphs or <=20 concise bullets. State the **complete engineering objective and all material functional/operational requirements needed for a fair solve**, grouped by meaningful system responsibility/invariant rather than by verifier case. Give the **what**, not the **how**. Do not omit a material requirement merely to make the prompt shorter or more human-looking. Do not tell the solver which component/function is incomplete, defective or responsible unless that fact would naturally be part of the handoff and is evidence-backed. Refer to solver-visible docs for architecture/layout/schemas/protocols/runbooks rather than duplicating those details in the instruction, but never move the actual task goal or material requirements into docs to evade the instruction limit. Apply Jira/Slack handoff and reverse-outline checks.

### 8. Q1 Spec Gap Repairer
Compare legitimate verifier-required behavior with `instruction.md` plus explicitly referenced solver-visible contracts. Close every material verifier->spec gap while preserving the instruction/documentation boundary: task objectives and material functional requirements stay discoverable as part of the solver-visible work request; detailed schemas/protocol semantics may live in legitimate referenced contracts. Do not copy test names, fixtures, hidden expected values, assertion ordering or implementation diagnosis into solver-visible prose. Never omit a material requirement for brevity.

### 9. Q2 Verifier Coverage Repairer
Rebuild the solver-visible requirement list and find any material spec->test gap. Add meaningful behavioral coverage rather than implementation checks or renamed duplicate fixtures. New/changed F2P cases require starter/NOP-fail and Oracle-pass evidence. Do not add cases merely to reach the strict numeric range.

### 10. Q3 Spec Ambiguity Repairer
Find competing interpretations that would change grading. Clarify authority, identities, ordering, failure/restart semantics, units, paths, or state transitions only where necessary. Preserve concise engineering-request style and implementation freedom.

### 11. Documentation Writer
Write reviewer-facing material from evidence. Do not call the environment a benchmark, fixture, cut-down reproduction or package built to demonstrate a bug.

### 12. Q7 Task Format Enforcer
Read the pinned creation-rule context plus current active enforcement/CI before checking exact task structure, `task.toml`, Dockerfiles, verifier image/launcher, solution layout, artifact boundaries, dependency pins, package isolation and forbidden files. Repair deterministic format issues before expensive runtime gates.

### 13. Task Assembly Agent
Run structure/metadata, lint/syntax, `.terminus/validate_task_complexity.py`, `.terminus/validate_runtime_authenticity.py`, Oracle, NOP, F2P/P2P empirical matrix and leakage checks. Confirm that strict LOC is substantive/reachable, F2P/edge/failure coverage is diverse rather than count-padding, and `instruction.md`/solver-visible docs respect the Edition 3 instruction-length and spec-file boundaries.

### 14. Complexity Governor
Challenge both scale and realism. Treat 3,000 LOC as a floor with no upper target. Ask whether the architecture naturally requires its code/resources/tests, whether 1,000 lines could disappear without changing the operational system, whether data is meaningfully varied, whether the work package is substantial rather than one localized defect, whether modules have differentiated production responsibilities, whether F2P cases represent distinct states/invariants rather than quota padding, and whether edge/negative/failure coverage is sufficient for the operational risk.

### 15. Runtime authenticity / deterministic validation / failure diagnosis
Run runtime-authenticity gates and exact Oracle/NOP/F2P/P2P validation on the candidate task commit. When deterministic execution fails, preserve the first meaningful failure and classify ownership. Q5 performs deep repair at the smallest responsible boundary: environment, build, dependency, startup, state, application, Oracle, verifier harness, infrastructure or contract. Never weaken a legitimate test simply to obtain green.

### 16. Freeze boundary
Only after all required deterministic validation succeeds may the controller record `FROZEN_CANDIDATE`. The freeze is a **state contract**, not a synonym for “latest branch looks good”: it binds the exact task commit, current rule context, current verifier/oracle evidence, current structure/complexity/runtime-authenticity evidence, and unresolved-conflict status. Any acceptance-relevant task/policy/validator change invalidates the freeze and routes back to the earliest affected stage.

## Frozen candidate quality interlock

After deterministic freeze, run two independent packet-bound reviews before normal Pre-LLMaJ:

### Q4 Spec-Test Contract Reviewer
Independently rebuild both mappings: requirement->test and substantive test behavior->discoverable requirement. It also checks grading-relevant ambiguity, that every material functional requirement remains solver-visible, and that completeness fixes did not turn `instruction.md` or environment docs into a hidden-test dump/prompt-extension loophole.

### Q6 Production Logic Auditor
Independently judge whether core solver-visible code/config is reachable, materially diverse, stateful/coupled and credible as production logic. Raw LOC/complexity-validator PASS is not enough; for strict tasks >=3,000 substantive reachable LOC remains required as a floor, with no upper target and no tolerance for padding.

`QUALITY_INTERLOCK_PASS` requires Q4 PASS + Q6 PASS, both with sufficient evidence and at least MEDIUM confidence on the exact task commit.

## Pre-model diagnostic simulation

After normal `PRE_LLMAJ: PASS`, run Q8 Model Perspective Difficulty Simulator twice in separate cold executions:
- `GPT_PERSPECTIVE`;
- `CLAUDE_PERSPECTIVE`.

Each perspective receives only solver-visible task evidence before attempting the solve. Do not show either the other result. These runs are diagnostic only, must be labeled simulation, and never replace Harbor LLMaJ or official GPT-5.5 x5 + Claude Opus 4.8 x5 trials.

## Flow

`CREATION_REQUEST -> RULE_RESOLUTION -> WORK_PACKAGE_RESEARCH -> SYSTEM_ARCHITECTURE(design-only) -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD(materialization) -> REFERENCE_SOLUTION -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT(Q1/Q2/Q3) -> DOCUMENTATION_DRAFT -> FORMAT_GATE(Q7) -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION(Q5 on failure) -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK(Q4/Q6) -> PRE_LLMAJ -> Q8 GPT/CLAUDE perspectives -> Harbor/model gates`

## Independence

- Every creator uses the pinned `CREATION_RULE_CONTEXT`; no creator silently substitutes a different repository rule baseline.
- The first A2 invocation is architecture design only and cannot consume/inject A3 defect topology.
- A3 designs against the approved clean architecture before the broken starter is materialized.
- The second A2 invocation materializes only the approved architecture/topology and does not invent extra defects.
- Environment Builder does not build by diffing against the final Oracle.
- Reference Solution Author does not use hidden tests as implementation recipes.
- Verifier Author does not calculate expected values from Oracle source.
- Instruction Writer/Q1 do not use hidden test names, fixture values or private defect IDs as a prose outline.
- Instruction Writer/Q1 do not hide material task goals in environment docs to bypass instruction limits.
- Q2 cannot remove a legitimate solver-visible requirement just to simplify the verifier.
- Q3 cannot add implementation requirements that were not part of the operational contract.
- Q4 and Q6 are read-only and cannot approve revisions they authored.
- Q5 cannot weaken legitimate verifier behavior to make Oracle green.
- Q8 simulations cannot see solution/tests/private design before their solve attempt and cannot claim to be official GPT/Claude evidence.
- Creator roles cannot issue the corresponding reviewer PASS.