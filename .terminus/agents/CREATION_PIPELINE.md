# Terminus Edition 3 Task Creation Pipeline

Creation policy version: `1.1`

Creation and independent review are separate systems. Before any producer starts, the Creation Controller resolves and pins the current Edition 3 task-rule context for the run. Every creator then uses that `CREATION_RULE_CONTEXT`, this file, `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/agents/QUALITY_AGENT_REGISTRY.md`, and its stage/role prompt. Producers create evidence and artifacts; they do not approve their own work.

Stage-specific prompt contracts override older shared prompt wording for their bounded execution phase. In particular, A2 phase execution is governed by `.terminus/agents/A2_PHASE_PROMPTS.md` and A9 assembly execution by `.terminus/agents/A9_ASSEMBLY_PROMPT.md`.

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

The resolved baseline is handed to creators as `CREATION_RULE_CONTEXT`. If applicable authoritative sources conflict, stop with `POLICY_CONFLICT` before scenario design. If governing task rules materially change during creation, the controller reruns rule resolution and reconciles/invalidates affected producer evidence before continuing.

## Default strict profile

Advanced/Frontier operational tasks use `large_system_strict` unless the controller records why a smaller task is inherently more realistic.

For `large_system_strict`, the default task shape is a **substantial production engineering work package**, not a single localized bug report. Suitable work packages include feature/reliability completion, migration completion, recovery implementation, platform modernization, operability completion, security hardening, state-model rework, integration completion, or incident-driven remediation whose required end state spans multiple coupled subsystems/invariants. An incident may explain why the work exists, but it should not be the sole source of difficulty.

Hard authoring constraints are minimum floors/ranges, not quotas or preferred target sizes:
- **at least 3,000 substantive, reachable solver-visible runtime/configuration LOC, with no upper target**;
- counted LOC must be meaningful production/domain implementation, not duplicated, generated/vendor, dead/unreachable, boilerplate-only, unnecessary or micro-module-inflated code;
- the solver-visible system must exhibit production characteristics appropriate to the domain: differentiated module responsibilities, real runtime/operator entrypoints, realistic state/data, validation/error handling, configuration, operational workflows, meaningful coupling, and persistence/restart/recovery/idempotency/failure behavior where applicable;
- infrastructure tasks use **30–50** meaningful interacting resources when that scale is natural;
- **20–30** defect manifestations from materially fewer root causes, with at least 15 manifestations participating in meaningful causal/interdependency edges;
- **25–30 non-duplicative F2P behavioral tests derived organically** from distinct operational requirements, states, transitions, failure modes and interactions;
- P2P according to actual preservation risk;
- sufficient domain-relevant edge, boundary, negative and failure-path coverage according to operational risk.

Negative/failure-path cases remain F2P or P2P according to starter-to-Oracle behavior. Do not manufacture edge cases, code, resources or tests merely to hit numeric targets. If a coherent task cannot naturally meet the profile, return `SCENARIO_TOO_SMALL`.

## Production-authenticity gate

Operational/stateful tasks also satisfy `.terminus/agents/PRODUCTION_AUTHENTICITY.md`.

Before `FROZEN_CANDIDATE`:
- the creation-rule context is current;
- when the task asserts inherited current-state or incident facts, build and validate the solver-visible **production evidence surface**; when no such facts are asserted, record the controller-owned not-applicable rationale instead of fabricating evidence;
- solver-visible current-state claims are supported by legitimate evidence when such claims are made;
- desired functional requirements are not disguised as incident evidence;
- data-backed strict tasks normally start with **10,000–20,000** deterministic, varied primary business records, unless the controller records a policy-allowed domain-specific exemption;
- major business modules contain substantive reachable domain logic;
- reject **thin business logic**, copied templates, dead/unreachable scale and quota-driven module/resource/test inflation;
- module/resource/test scale is structurally necessary rather than quota-driven;
- normal, edge, boundary, negative and failure-path behavior is sufficiently represented;
- `.terminus/validate_runtime_authenticity.py <task>` passes.

For COBOL/business-language systems, reject “one IF = one program” construction and other thin logic padded by declarations/dead paragraphs.

## Instruction / documentation boundary

Edition 3 allows `instruction.md` to be concise as **<=2 short paragraphs or <=20 bullets**. For large strict tasks, up to 20 concise bullets is acceptable when needed to state the complete material work package.

`instruction.md` owns the engineering objective plus material functional/operational, preservation, compatibility and safety requirements and required outputs. Solver-visible technical docs may own repository/component layout, runtime/operator entrypoints, architecture/state models, schemas, protocol semantics, APIs/CLIs and runbooks. Docs must not become a second prompt used to hide material task goals or repair guidance.

The desired separation is: **instruction = what must work; docs/contracts = how the inherited system is organized and governed; code/runtime state = what is currently implemented; solver = determine the implementation gaps and repair them.**

Before A7, the Creation Controller constructs the schema-valid `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT` defined by `.terminus/agents/INSTRUCTION_POLICY.md`. A7 consumes that sanitized projection rather than private defect topology, hidden verifier material, Oracle diffs or prior reviews.

## Mandatory producer sequence

### 0. Creation Controller — Rule Resolution
Resolve and pin the authoritative task-rule baseline, active validators, creation profile and environment/network constraints. No producer stage starts until `CREATION_RULE_CONTEXT` is available and any policy conflict is resolved.

### 1. Scenario Researcher
Produce 3–5 credible **engineering work-package** candidates. For each define the engineering objective, persona, required end state, major coupled requirement families, inherited system/state, originality references and scale fit. Confirm strict scope can naturally support substantive production scale, organic F2P diversity and realistic normal/edge/failure behavior without filler.

### 2A. System Architect — clean architecture design
Design only the inherited production system shape before any private defect/incomplete-behavior topology exists. Produce the component/resource graph, runtime/operator entrypoints, state/persistence model, solver-visible technical-documentation plan, production characteristics, scale fit and reachability plan. **Do not create the broken starter and do not inject defects at this stage.** The output is the clean architecture contract consumed by A3.

### 3. Defect Topology Designer
Against the approved clean architecture, design 4–8 root-cause clusters and 20–30 manifestations with at least 15 manifestations participating in meaningful causal/interdependency edges, plus cross-component/cross-cluster relationships and plausible partial-fix traps. Build behavioral surfaces spanning normal, edge/boundary, negative/rejection, failure/recovery and cross-component behavior. Return `SCENARIO_TOO_SMALL` instead of padding.

### 2B. Environment Builder — starter materialization
Re-invoke A2 only after the A3 topology is approved. `ENVIRONMENT_BUILD` requires the clean architecture, approved defect topology and `SOLVER_VISIBLE_DOC_PLAN`. Materialize the solver-visible runtime/state/config/docs from those approved inputs. Inject only approved defect/incomplete behaviors. If the architecture cannot support the planned behavior, return `ARCHITECTURE_GAP`; do not invent an untracked defect or silently rewrite the architecture.

The canonical phase order is `SYSTEM_ARCHITECTURE(design-only) -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD(materialization)`.

### 4. Reference Solution Author
Repair/complete the approved operational invariants without reading hidden verifier bodies before the first Oracle implementation is frozen. No fixture/test special casing.

### 5. Verifier Author
Build behavioral tests from solver-visible requirements/contracts. Strict profile uses 25–30 F2P cases only when they arise organically from materially distinct operational behavior. Add P2P according to actual preservation risk and include sufficient edge/boundary/negative/failure-path behavior. Q4 is not invoked here; the independent Q4 review happens only after freeze.

### 6. Human Writing Researcher
Use real public Jira/issues/change requests/engineering tickets and incident handoffs as information-selection calibration. Distinguish required end-state behavior from asserted current-state facts and avoid invented implementation diagnoses/backstory.

### 7. Instruction Writer
Consume the current `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT` plus writing calibration. Write <=2 short paragraphs or <=20 concise bullets containing the complete material work request, grouped by system responsibility/invariant. Give the what, not the how. Do not recover missing requirements from private topology, hidden tests or Oracle knowledge.

### 8. Q1 Spec Gap Repairer
Close legitimate verifier->spec gaps while preserving the instruction/documentation boundary. Never copy hidden test names, private defect IDs, fixture values or implementation diagnosis into solver-facing prose.

### 9. Q2 Verifier Coverage Repairer
Find material spec->test gaps and add meaningful behavioral coverage. New/changed F2P cases require starter/NOP-fail and Oracle-pass evidence. Do not manufacture cases to reach a count.

### 10. Q3 Spec Ambiguity Repairer
Clarify grading-relevant ambiguity while preserving engineering-request style and implementation freedom. Q1/Q2/Q3 are producer-side alignment; they do not substitute for Q4.

### 11. Documentation Writer
Write reviewer-facing material from evidence. Do not call the environment a benchmark, fixture, cut-down reproduction or package built to demonstrate a bug.

### 12. Q7 Task Format Enforcer
Apply current exact folder/task.toml/Docker/verifier/solution/package/isolation rules before expensive runtime gates.

### 13. Task Assembly Agent
A9 uses `.terminus/agents/A9_ASSEMBLY_PROMPT.md`. Assemble producer outputs into an internally coherent candidate and perform assembly-local task-tree, metadata, static/lint, instruction/docs and leakage/package checks. Prepare evidence for the later gate owners. Return `ASSEMBLED | RETURN_TO_PRODUCER | BLOCKED`.

A9 **does not** return `FROZEN_CANDIDATE`, issue Complexity Governor PASS, issue runtime-authenticity PASS, or own Oracle/NOP/F2P/P2P execution. `ASSEMBLED` routes only to `COMPLEXITY_GATE`.

### 14. Complexity Governor
Independently challenge scale and realism. Treat 3,000 LOC as a floor with no upper target. Validate substantive/reachable code, differentiated responsibilities, causal breadth, F2P organicity, edge/failure coverage and anti-padding properties. Q6 is not invoked here; Q6 is reserved for the post-freeze quality interlock.

### 15. Runtime authenticity / deterministic validation / failure diagnosis
After Complexity Governor PASS, the controller runs `RUNTIME_AUTHENTICITY`, then exact `DETERMINISTIC_VALIDATION` for Oracle reward 1, NOP reward 0 and F2P/P2P empirical matrices. When deterministic execution fails, preserve the first meaningful failure and route Q5 to the smallest responsible boundary. Do not weaken a legitimate test to obtain green.

### 16. Freeze boundary
Only after all required deterministic validation succeeds may the controller record `FROZEN_CANDIDATE`. The freeze is a **state contract**, not a producer status or synonym for “latest branch looks good”. It binds the exact task commit, rule context, format/complexity/runtime-authenticity state, Oracle/NOP/F2P/P2P evidence and unresolved-conflict status.

No pre-freeze stage may invoke Q4 or Q6 as an acceptance reviewer. Any acceptance-relevant task/policy/validator change invalidates the freeze and routes back to the earliest affected stage.

## Frozen candidate quality interlock

After deterministic freeze, run two independent packet-bound reviews before normal Pre-LLMaJ:

### Q4 Spec-Test Contract Reviewer
Independently rebuild requirement->test and substantive-test->discoverable-requirement mappings, ambiguity, instruction completeness and documentation-boundary integrity.

### Q6 Production Logic Auditor
Independently judge whether solver-visible production code/config is reachable, materially diverse, coupled/stateful and credible as production logic. Raw LOC/complexity-validator PASS is not enough.

`QUALITY_INTERLOCK_PASS` requires Q4 PASS + Q6 PASS with sufficient evidence and at least MEDIUM confidence under their current packet/freshness rules.

## Pre-model diagnostic simulation

After normal `PRE_LLMAJ: PASS`, run Q8 twice in separate cold executions (`GPT_PERSPECTIVE`, `CLAUDE_PERSPECTIVE`). Each sees only solver-visible task evidence before solving. These runs are diagnostic only and never replace Harbor LLMaJ or official model trials.

## Flow

`CREATION_REQUEST -> RULE_RESOLUTION -> WORK_PACKAGE_RESEARCH -> SYSTEM_ARCHITECTURE(design-only) -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD(materialization) -> REFERENCE_SOLUTION -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT(Q1/Q2/Q3) -> DOCUMENTATION_DRAFT -> FORMAT_GATE(Q7) -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION(Q5 on failure) -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK(Q4/Q6) -> PRE_LLMAJ -> Q8 GPT/CLAUDE perspectives -> Harbor/model gates`

## Independence

- Every creator uses the pinned `CREATION_RULE_CONTEXT`.
- A2 architecture design cannot consume/inject A3 topology; A3 precedes starter materialization.
- A2 materialization injects only approved topology and does not read the final Oracle.
- Reference Solution Author does not use hidden tests as implementation recipes.
- Verifier Author does not calculate expected values from Oracle source.
- A7/Q1 do not use hidden tests/private defects/Oracle diffs as a prose outline and do not hide material goals in docs.
- Q2 cannot remove a legitimate solver-visible requirement merely to simplify the verifier.
- Q3 cannot add implementation requirements outside the operational contract.
- A9 cannot create or imply freeze.
- Q4 and Q6 are read-only, packet-bound post-freeze reviewers and are not invoked as pre-freeze semantic reviewers.
- Q5 cannot weaken legitimate verifier behavior to make Oracle green.
- Q8 simulations cannot see solution/tests/private design before their solve attempt and cannot claim to be official model evidence.
- Creator roles cannot issue the corresponding reviewer PASS.
