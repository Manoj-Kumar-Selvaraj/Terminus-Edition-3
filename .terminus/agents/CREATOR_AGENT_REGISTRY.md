# Terminus Edition 3 Creator Agent Registry

Registry version: `1.0`

This registry defines the producer agents used before independent review. Current Edition 3 rules always override this registry. Producers create or repair artifacts; they never issue final acceptance verdicts for their own work.

## Large-system profile

For Advanced/Frontier task creation, use `large_system` unless the controller explicitly records why a smaller system is more realistic.

Mandatory authoring targets for `large_system`:

- >= 3,000 substantive solver-visible runtime/configuration LOC. Exclude tests, solution, docs, generated/vendor content, blank lines, comments-only lines and duplicated filler.
- Infrastructure tasks: 30-50 meaningful resources whose relationships affect observable behavior.
- 20-30 tracked defect manifestations derived from materially fewer root-cause clusters.
- >= 15 defect manifestations participating in causal/interdependency edges.
- 25-30 F2P behavioral tests. Every F2P must fail against the starter/NOP state for a substantive reason and pass against Oracle.
- P2P/regression tests are added only where already-correct behavior needs protection; no fixed P2P quota.
- The instruction remains concise and incident-oriented. It must not enumerate the defect graph or hidden test inventory.

If the scenario cannot meet these targets without padding, hidden requirements or unrelated bugs, return `SCENARIO_TOO_SMALL` and select a richer scenario.

## Producer agents

### A1 — Scenario Researcher

Owns incident discovery, operational persona, system boundary, public-reference research and duplicate-risk analysis. Produces 3-5 structurally different candidates. Learns failure shapes from public incidents but never copies issue wording, benchmark topology or requirement ordering.

### A2 — System Architect / Environment Builder

Owns the solver-visible code/configuration system, fixtures, runtime topology, Docker environment and operational artifacts. Must prove runtime reachability for counted modules/resources and must not use generated/dead code to hit the scale floor. Does not read the final Oracle while building the starter.

### A3 — Defect Topology Designer

Owns `.terminus/designs/<task>.json`. Starts from 4-8 root-cause clusters and derives 20-30 manifestations with explicit causal edges and plausible partial-fix traps. At least 15 manifestations must participate in the graph. Does not design one isolated source typo per test.

### A4 — Reference Solution Author

Owns the deterministic general repair from the approved solver-visible contract. Does not read hidden verifier bodies before the first Oracle implementation is frozen. Restores durable invariants rather than patching fixture-specific outputs.

### A5 — Verifier Author

Owns behavioral tests and `.terminus/designs/<task>-test-map.json`. Creates 25-30 independent F2P scenarios for `large_system`, plus P2P where needed. Tests observable behavior/state, not preferred implementation syntax. Every F2P must be empirically NOP-fail/Oracle-pass before candidate freeze.

### A6 — Human Writing Corpus Researcher

Owns public human-engineering writing calibration. Searches real issue/incident/ticket sources across multiple ecosystems, verifies source provenance, and records only metadata plus generalized information-selection observations. Never copies long prose or turns source wording into a template. Produces/maintains the human engineering source corpus and a per-task calibration sample packet.

### A7 — Instruction Writer

Owns `instruction.md`. Receives the incident, solver-visible docs/contracts, approved operational invariants and a calibration packet from A6. It must not receive hidden test names/bodies, private defect IDs or the Oracle diff as a sentence checklist. Writes the shortest fair Jira/Slack/on-call style handoff that satisfies current Edition 3 instruction rules.

### A8 — Documentation Writer

Owns reviewer-facing README and Difficulty/Solution/Verification explanations after functional evidence exists. Does not inflate solver-facing instructions and does not claim empirically proven difficulty before trials.

### A9 — Task Assembly Agent

Integrates producer outputs and runs deterministic authoring checks: file structure, metadata, build inputs, lint/syntax, complexity profile, Oracle, NOP, F2P/P2P empirical matrix and leakage/package hygiene. It cannot approve its own task.

### A10 — Complexity Governor

Independently challenges scale authenticity. It rejects dead-code/resource/test inflation even if numeric floors pass. Mandatory questions include whether 1,000 lines could be deleted without changing the operational system, whether resources are meaningful dependencies, and whether tests are real state/invariant variations rather than fixture renames.

### A11 — Authoring Failure Diagnostician

Owns Oracle/NOP authoring failures before semantic review. Reads CI/Harbor evidence and classifies the first meaningful failure as one of:

- `environment_authoring_bug`
- `oracle_implementation_bug`
- `verifier_authoring_bug`
- `starter_state_bug`
- `contract_gap`
- `infrastructure/transient`

It routes only the smallest implicated layer back to the responsible producer. It must not weaken a legitimate behavioral test merely to obtain reward 1/0. Multiple failing tests that share one authoring root cause are treated as one repair problem.

## Creation order

`A1 Scenario Researcher -> A2 System Architect -> A3 Defect Topology -> A4 Reference Solution -> A5 Verifier Author -> A6 Human Writing Corpus Researcher -> A7 Instruction Writer -> A8 Documentation Writer -> A9 Task Assembly -> A10 Complexity Governor -> deterministic Oracle/NOP`

If Oracle/NOP fails, invoke `A11 Authoring Failure Diagnostician`, route the narrow repair, and repeat A9/A10 as affected.

Only a deterministic frozen candidate enters the independent review system.

## Isolation rules

- A2 must not construct starter state by diffing against the final Oracle.
- A4 must not read hidden verifier bodies before its first implementation is frozen.
- A5 must not use Oracle source as its expected-value calculator.
- A6 may read public sources but cannot write task requirements from them.
- A7 must not see test/defect inventories as prose inputs.
- A9/A10 cannot substitute numeric success for realism or task quality.
- No producer can issue the corresponding independent reviewer PASS.
