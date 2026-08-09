# Terminus Edition 3 Creator Agent Registry

Registry version: `1.0`

Producer roles create/repair task artifacts before independent review. Every producer reads current Edition 3 rules, `.terminus/agents/CREATION_PIPELINE.md`, and `.terminus/agents/PRODUCTION_AUTHENTICITY.md`. Producers never issue final acceptance for their own work.

The creator system is extended by `.terminus/agents/QUALITY_AGENT_REGISTRY.md`. Q1, Q2, Q3, Q5 and Q7 are producer/fixer roles; Q4, Q6 and Q8 are independent/diagnostic quality roles and cannot approve work they authored.

## `large_system_strict`

Default for large production-style Advanced/Frontier authoring unless a smaller profile is explicitly justified:
- >= **3,000** substantive solver-visible runtime/configuration LOC;
- infrastructure: **30–50** meaningful interacting resources;
- **20–30** defect manifestations from fewer root causes;
- >=15 interrelated manifestations;
- **25–30** F2P tests;
- P2P as needed.

If natural scope cannot meet this without filler, return `SCENARIO_TOO_SMALL`.

## Production authenticity

For operational/stateful strict tasks:
- require solver-visible incident logs plus handoff/state/operator evidence;
- data-backed tasks normally start with **10,000–20,000** deterministic varied primary records;
- reject thin business logic or micro-program/module inflation;
- reject benchmark/fixture framing in incident prose;
- require `.terminus/validate_runtime_authenticity.py` PASS in addition to the ordinary complexity gate.

## Producer agents

### A1 — Scenario Researcher
Owns incident discovery, persona, evidence that would exist after the incident, scale fit, public-reference research and duplicate risk.

### A2 — System Architect / Environment Builder
Owns runtime topology, realistic state/data, solver-visible incident evidence and starter code/config. Major modules must be reachable and substantive. It does not read the final Oracle while building the starter.

### A3 — Defect Topology Designer
Owns the private causal graph: normally 4–8 root causes, 20–30 manifestations, cross-component/cross-cluster edges and partial-fix traps.

### A4 — Reference Solution Author
Owns the deterministic general repair. No hidden-test special casing.

### A5 — Verifier Author
Owns behavioral verifier and private test map. Strict tasks use 25–30 independent F2P cases plus P2P as needed; F2P is empirically starter-fail/Oracle-pass.

### A6 — Human Writing Corpus Researcher / Human Writing Researcher
Owns public source-backed calibration. It extracts information-selection patterns, never a phrase bank. It applies the incident-evidence test and must flag invented production backstory.

### A7 — Instruction Writer
Owns `instruction.md`. It points to actual logs/state/runbooks, states the operational ask, and avoids hidden-test-shaped completeness.

### A8 — Documentation Writer
Owns README and submission explanations. It must not describe the task as a benchmark, fixture, cut-down reproduction, or package built for evaluation.

### A9 — Task Assembly Agent
Runs structure, metadata, lint, complexity, runtime-authenticity, Oracle/NOP and leakage gates.

### A10 — Complexity Governor
Challenges padding, toy state, micro-module inflation and task realism even when numeric minima pass.

### A11 — Authoring Failure Diagnostician
Classifies deterministic failures as environment/oracle/verifier/starter/contract/infrastructure and routes only the implicated layer.

## Quality repair overlay

After the verifier and instruction exist, the Orchestrator runs the repair-capable quality agents before expensive review:

- **Q1 Spec Gap Repairer** — closes test-required behavior missing from solver-visible spec using natural invariant-level wording, never a test dump.
- **Q2 Verifier Coverage Repairer** — closes solver-visible requirements that lack meaningful behavioral tests.
- **Q3 Spec Ambiguity Repairer** — removes grading-relevant ambiguity while preserving implementation freedom.
- **Q7 Task Format Enforcer** — repairs exact task/task.toml/Docker/verifier/solution/package-format defects from current rules.
- **Q5 Oracle & Runtime Repair Specialist** — invoked only when Oracle/build/runtime evidence fails; repairs the smallest responsible layer and never weakens legitimate tests.

After deterministic freeze, **Q4 Spec-Test Contract Reviewer** and **Q6 Production Logic Auditor** independently judge alignment and production-grade logic before Pre-LLMaJ. **Q8 Model Perspective Difficulty Simulator** runs two diagnostic cold solve perspectives after Pre-LLMaJ PASS and before expensive official model-backed difficulty trials.

## Creation order

`A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> A7 -> Q1 -> Q2 -> Q3 -> A8 -> Q7 -> A9 -> A10 -> deterministic Oracle/NOP (Q5 on failure)`

Only a frozen deterministic candidate that also passes the Q4/Q6 quality interlock enters normal Pre-LLMaJ review.
