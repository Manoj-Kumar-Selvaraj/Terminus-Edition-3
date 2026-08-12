# Terminus Edition 3 Creator Agent Registry

Registry version: `1.0`

Producer roles create/repair task artifacts before independent review. Every producer reads current Edition 3 rules, `.terminus/agents/CREATION_PIPELINE.md`, and `.terminus/agents/PRODUCTION_AUTHENTICITY.md`. Producers never issue final acceptance for their own work.

The creator system is extended by `.terminus/agents/QUALITY_AGENT_REGISTRY.md`. Q1, Q2, Q3, Q5 and Q7 are producer/fixer roles; Q4, Q6 and Q8 are independent/diagnostic quality roles and cannot approve work they authored.

## `large_system_strict`

Default for large production-style Advanced/Frontier authoring unless a smaller profile is explicitly justified. Numeric requirements are minimum floors/ranges, not quotas:
- **>=3,000 substantive, reachable solver-visible runtime/configuration LOC with no upper target**; 5,000+ or larger is valid when naturally required by the production architecture;
- LOC must come from meaningful production/domain implementation, not duplicated, generated/vendor, dead/unreachable, unnecessary, boilerplate-only or micro-module-inflated code;
- the system must exhibit credible production characteristics appropriate to the domain, including differentiated responsibilities/modules, real entrypoints, realistic state/data, validation/error handling, configuration, operational workflows, meaningful coupling, and persistence/restart/recovery/idempotency/failure handling where applicable;
- infrastructure: **30–50** meaningful interacting resources when that scale is natural;
- **20–30** defect manifestations from fewer root causes;
- >=15 interrelated manifestations;
- **25–30 F2P tests reached organically** from materially distinct requirements, states, transitions, failure modes and interactions rather than count padding;
- P2P according to actual regression risk;
- sufficient domain-relevant edge, boundary, negative and failure-path behavior. Negative cases remain F2P or P2P according to their starter-to-Oracle transition.

If natural scope cannot meet the production scale, behavioral diversity or edge/failure coverage without filler, return `SCENARIO_TOO_SMALL`.

## Production authenticity

For operational/stateful strict tasks:
- require solver-visible incident logs plus handoff/state/operator evidence;
- data-backed tasks normally start with **10,000–20,000** deterministic varied primary records;
- reject thin business logic, dead/unreachable scale, duplicated code, copied resources or micro-program/module inflation;
- reject F2P/test inflation, renamed fixture variants and artificial edge cases created only to hit a count;
- reject benchmark/fixture framing in incident prose;
- require `.terminus/validate_runtime_authenticity.py` PASS in addition to the ordinary complexity gate.

## Producer agents

### A1 — Scenario Researcher
Owns incident discovery, persona, evidence that would exist after the incident, scale fit, public-reference research and duplicate risk. It must select incidents that can naturally support the required production code depth, behavioral diversity and edge/failure surface without filler.

### A2 — System Architect / Environment Builder
Owns runtime topology, realistic state/data, solver-visible incident evidence and starter code/config. Major modules must be reachable, substantive and differentiated by real production responsibility. It does not read the final Oracle while building the starter.

### A3 — Defect Topology Designer
Owns the private causal graph: normally 4–8 root causes, 20–30 manifestations, cross-component/cross-cluster edges and partial-fix traps.

### A4 — Reference Solution Author
Owns the deterministic general repair. No hidden-test special casing.

### A5 — Verifier Author
Owns behavioral verifier and private test map. Strict tasks use 25–30 independent F2P cases only when organically supported by materially distinct operational behavior, plus P2P according to regression risk and sufficient edge/boundary/negative/failure-path cases. F2P is empirically starter-fail/Oracle-pass; negative cases use F2P or P2P rather than a third taxonomy.

### A6 — Human Writing Corpus Researcher / Human Writing Researcher
Owns public source-backed calibration. It extracts information-selection patterns, never a phrase bank. It applies the incident-evidence test and must flag invented production backstory.

### A7 — Instruction Writer
Owns `instruction.md`. It points to actual logs/state/runbooks, states the operational ask, and avoids hidden-test-shaped completeness.

### A8 — Documentation Writer
Owns README and submission explanations. It must not describe the task as a benchmark, fixture, cut-down reproduction, or package built for evaluation.

### A9 — Task Assembly Agent
Runs structure, metadata, lint, complexity, runtime-authenticity, Oracle/NOP and leakage gates, including evidence that LOC/test/resource scale is substantive rather than quota-driven.

### A10 — Complexity Governor
Challenges padding, toy state, duplicated/unreachable code, micro-module inflation, F2P quota-padding, insufficient edge/failure coverage and task realism even when numeric minima pass.

### A11 — Authoring Failure Diagnostician
Classifies deterministic failures as environment/oracle/verifier/starter/contract/infrastructure and routes only the implicated layer.

## Quality repair overlay

After the verifier and instruction exist, the Orchestrator runs the repair-capable quality agents before expensive review:

- **Q1 Spec Gap Repairer** — closes test-required behavior missing from solver-visible spec using natural invariant-level wording, never a test dump.
- **Q2 Verifier Coverage Repairer** — closes solver-visible requirements that lack meaningful behavioral tests; it must not manufacture cases merely to satisfy the strict count range.
- **Q3 Spec Ambiguity Repairer** — removes grading-relevant ambiguity while preserving implementation freedom.
- **Q7 Task Format Enforcer** — repairs exact task/task.toml/Docker/verifier/solution/package-format defects from current rules.
- **Q5 Oracle & Runtime Repair Specialist** — invoked only when Oracle/build/runtime evidence fails; repairs the smallest responsible layer and never weakens legitimate tests.

After deterministic freeze, **Q4 Spec-Test Contract Reviewer** and **Q6 Production Logic Auditor** independently judge alignment and production-grade logic before Pre-LLMaJ. **Q8 Model Perspective Difficulty Simulator** runs two diagnostic cold solve perspectives after Pre-LLMaJ PASS and before expensive official model-backed difficulty trials.

## Creation order

`A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> A7 -> Q1 -> Q2 -> Q3 -> A8 -> Q7 -> A9 -> A10 -> deterministic Oracle/NOP (Q5 on failure)`

Only a frozen deterministic candidate that also passes the Q4/Q6 quality interlock enters normal Pre-LLMaJ review.
