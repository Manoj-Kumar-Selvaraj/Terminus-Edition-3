# Terminus Edition 3 Creator Agent Registry

Registry version: `1.0`

Producer roles create/repair task artifacts before independent review. Every producer reads current Edition 3 rules, `.terminus/agents/CREATION_PIPELINE.md`, and `.terminus/agents/PRODUCTION_AUTHENTICITY.md`. Producers never issue final acceptance for their own work.

The creator system is extended by `.terminus/agents/QUALITY_AGENT_REGISTRY.md`. Q1, Q2, Q3, Q5 and Q7 are producer/fixer roles; Q4, Q6 and Q8 are independent/diagnostic quality roles and cannot approve work they authored. Q4 and Q6 are post-freeze packet-bound reviewers and are not producer-side semantic reviewers.

## `large_system_strict`

Default for large production-style Advanced/Frontier authoring unless a smaller profile is explicitly justified. The default task shape is a **substantial coherent engineering work package**, not a localized bug report padded into a large environment. Numeric requirements are minimum floors/ranges, not quotas:
- **>=3,000 substantive, reachable solver-visible runtime/configuration LOC with no upper target**; 5,000+ or larger is valid when naturally required by the production architecture;
- LOC must come from meaningful production/domain implementation, not duplicated, generated/vendor, dead/unreachable, unnecessary, boilerplate-only or micro-module-inflated code;
- the system must exhibit credible production characteristics appropriate to the domain, including differentiated responsibilities/modules, real entrypoints, realistic state/data, validation/error handling, configuration, operational workflows, meaningful coupling, and persistence/restart/recovery/idempotency/failure handling where applicable;
- infrastructure: **30–50** meaningful interacting resources when that scale is natural;
- **20–30** defect/incomplete-behavior manifestations from fewer root causes;
- >=15 interrelated manifestations;
- **25–30 F2P tests reached organically** from materially distinct requirements, states, transitions, failure modes and interactions rather than count padding;
- P2P according to actual regression risk;
- sufficient domain-relevant edge, boundary, negative and failure-path behavior. Negative cases remain F2P or P2P according to their starter-to-Oracle transition.

If natural scope cannot meet the production scale, coupled requirement breadth, behavioral diversity or edge/failure coverage without filler/unrelated requirements, return `SCENARIO_TOO_SMALL`.

## Instruction / documentation boundary

Edition 3 allows `instruction.md` to use **<=2 short paragraphs or <=20 concise bullets**. Strict tasks may use as many concise bullets as materially needed up to 20.

`instruction.md` owns the engineering objective plus all material functional/operational, preservation, compatibility and safety requirements needed for a fair solve. Solver-visible docs may explain repository/folder/component layout, architecture/state models, runtime/operator entrypoints, schemas/record layouts, protocol semantics, API/CLI contracts and runbooks. Docs must not become a second prompt used to hide the task goal/material requirements or expose the repair plan.

The normal boundary is: **instruction = what must work; docs/contracts = how the inherited system is organized/governed; code/runtime = what exists now; solver = determine implementation gaps and repair/complete them.**

A7 receives the controller-produced `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT` defined by `.terminus/agents/INSTRUCTION_POLICY.md` and `.terminus/agents/schemas/solver_visible_requirement_contract.schema.json`. It must not reconstruct missing requirements from private defect topology, hidden verifier material, Oracle diffs or prior reviews.

## Production authenticity

For operational/stateful strict tasks:
- require solver-visible logs/state/handoff/operator evidence when the task asserts inherited current-state/incident facts;
- desired functional requirements need not be narrated as incident evidence;
- data-backed tasks normally start with **10,000–20,000** deterministic varied primary records;
- reject thin business logic, dead/unreachable scale, duplicated code, copied resources or micro-program/module inflation;
- reject F2P/test inflation, renamed fixture variants and artificial edge cases created only to hit a count;
- reject benchmark/fixture framing and invented implementation diagnoses in solver-facing prose;
- require `.terminus/validate_runtime_authenticity.py` PASS in addition to the ordinary complexity gate.

## Producer agents

### A1 — Scenario Researcher
Owns engineering work-package discovery: objective/end state, major coupled requirement families, inherited production system/state, persona, public-reference research, duplicate risk and scale fit. For strict tasks it must reject one localized incident/bug unless the contained environment naturally supports the required production and behavioral breadth without padding.

### A2 — System Architect / Environment Builder
A2 is invoked in **two distinct stages with different contracts** and must not collapse them into one pass.

**Architecture-design invocation (`SYSTEM_ARCHITECTURE`)** owns only the clean inherited-system design: component/resource graph, runtime/operator entrypoints, state/persistence model, technical-documentation plan, production characteristics, scale fit and reachability plan. It must not inject defects, create the broken starter, or consume private defect topology that does not exist yet.

**Environment-materialization invocation (`ENVIRONMENT_BUILD`)** runs only after A3 has produced the approved defect/incomplete-behavior topology. It materializes the solver-visible runtime, realistic state/data, technical docs, current-state evidence where appropriate, and starter code/config according to the clean architecture plus the approved topology. Major modules must be reachable, substantive and differentiated by real production responsibility. Docs explain structure/contracts without becoming a prompt extension or telling the solver where the repair is. It does not read the final Oracle while building the starter and does not add untracked surprise defects.

### A3 — Defect Topology Designer
Owns the private causal graph and behavioral-surface design **against the approved clean architecture before the starter is materialized**: normally 4–8 root causes, 20–30 manifestations, at least 15 strict-profile manifestations participating in meaningful causal/interdependency edges, cross-component/cross-cluster relationships and partial-fix traps. It maps normal, edge/boundary, negative/rejection, failure/recovery and cross-component surfaces so later F2P coverage can arise organically, without one defect per test or count-driven manifestations. If that breadth cannot arise naturally, it returns `SCENARIO_TOO_SMALL`.

### A4 — Reference Solution Author
Owns the deterministic general repair/completion. No hidden-test special casing.

### A5 — Verifier Author
Owns behavioral verifier and private test map. Strict tasks use 25–30 independent F2P cases only when organically supported by materially distinct operational behavior, plus P2P according to regression risk and sufficient edge/boundary/negative/failure-path cases. F2P is empirically starter-fail/Oracle-pass; negative cases use F2P or P2P rather than a third taxonomy.

### A6 — Human Writing Corpus Researcher / Human Writing Researcher
Owns public source-backed calibration across substantial Jira/issues/change requests as well as incident handoffs. It extracts information-selection patterns, never a phrase bank; distinguishes desired end state from current-state evidence; and flags invented backstory or implementation diagnosis.

### A7 — Instruction Writer
Owns `instruction.md`. It consumes the current schema-valid `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT`, states the complete engineering objective and all material functional/operational requirements within <=2 short paragraphs or <=20 concise bullets, uses solver-visible docs for technical structure/contracts, and avoids implementation diagnosis, prompt-extension docs and hidden-test-shaped completeness.

### A8 — Documentation Writer
Owns README and submission explanations. It must not describe the task as a benchmark, fixture, cut-down reproduction, or package built for evaluation.

### A9 — Task Assembly Agent
Owns **assembly only**: task-tree coherence, metadata/static/lint readiness, instruction/docs boundary checks, package/leakage boundaries, and preparation of evidence consumed by later gates. Its executable contract is `.terminus/agents/A9_ASSEMBLY_PROMPT.md`. A9 returns `ASSEMBLED`, not `FROZEN_CANDIDATE`, and does not issue Complexity Governor PASS, runtime-authenticity PASS, Oracle/NOP/F2P/P2P evidence, Q4 PASS or Q6 PASS.

### A10 — Complexity Governor
Challenges localized-task padding, toy state, duplicated/unreachable code, micro-module inflation, F2P quota-padding, insufficient edge/failure coverage, instruction/docs leakage and task realism even when numeric minima pass.

### A11 — Authoring Failure Diagnostician
Classifies deterministic failures as environment/oracle/verifier/starter/contract/infrastructure and routes only the implicated layer.

## Quality repair overlay

After the verifier and instruction exist, the Orchestrator runs the repair-capable quality agents before expensive review:

- **Q1 Spec Gap Repairer** — closes legitimate graded behavior missing from solver-visible specification while keeping the complete material work request discoverable and preserving the instruction/docs boundary; never a test dump.
- **Q2 Verifier Coverage Repairer** — closes solver-visible requirements that lack meaningful behavioral tests; it must not manufacture cases merely to satisfy the strict count range.
- **Q3 Spec Ambiguity Repairer** — removes grading-relevant ambiguity while preserving implementation freedom.
- **Q7 Task Format Enforcer** — repairs exact task/task.toml/Docker/verifier/solution/package-format defects from current rules.
- **Q5 Oracle & Runtime Repair Specialist** — invoked only when Oracle/build/runtime evidence fails; repairs the smallest responsible layer and never weakens legitimate tests.

After `ASSEMBLY`, A10 owns `COMPLEXITY_GATE`, then the controller owns `RUNTIME_AUTHENTICITY` and `DETERMINISTIC_VALIDATION`. Only after those gates pass may the controller record `FROZEN_CANDIDATE`.

After deterministic freeze, **Q4 Spec-Test Contract Reviewer** and **Q6 Production Logic Auditor** independently judge alignment and production-grade logic at `QUALITY_INTERLOCK` before Pre-LLMaJ. They do not appear as semantic reviewers on pre-freeze creation stages. Q4 also checks that complete functional requirements remain solver-visible without turning either `instruction.md` or environment docs into a hidden-test/prompt-extension dump. **Q8 Model Perspective Difficulty Simulator** runs two diagnostic cold solve perspectives after Pre-LLMaJ PASS and before expensive official model-backed difficulty trials.

## Creation order

`A1 -> A2(SYSTEM_ARCHITECTURE design-only) -> A3 -> A2(ENVIRONMENT_BUILD materialization) -> A4 -> A5 -> A6 -> A7 -> Q1 -> Q2 -> Q3 -> A8 -> Q7 -> A9(ASSEMBLED) -> A10 -> runtime-authenticity -> deterministic Oracle/NOP (Q5 on failure) -> FROZEN_CANDIDATE -> Q4/Q6 QUALITY_INTERLOCK`

Only a frozen deterministic candidate that also passes the Q4/Q6 quality interlock enters normal Pre-LLMaJ review.
