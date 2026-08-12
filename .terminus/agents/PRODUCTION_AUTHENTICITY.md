# Terminus Production Authenticity Policy

Policy version: `1.1`

This policy augments the Edition 3 creator and reviewer rules for tasks that claim to model an operational, production, stateful, or large-system incident. It is a local authoring gate, not a replacement for official Edition 3 acceptance rules.

## Production evidence surface

A production incident must leave solver-visible evidence. At least one incident log plus one independent operational artifact such as a shift handoff, persisted state snapshot, failed-run status, or operator note must support the incident described in `instruction.md`.

Do not invent a polished production story with no evidence in the environment. The instruction should point the solver to the evidence rather than restating every hidden acceptance condition.

Reject benchmark framing in solver/reviewer prose such as “cut-down reproduction”, “benchmark fixture”, “this package is used to reproduce”, or prose that explains why the task exists instead of what the operator observed.

## Production-system characteristics

Production authenticity is primarily structural and operational, not numerical. For `large_system_strict`, **3,000 substantive reachable solver-visible runtime/configuration LOC is a floor with no upper target**, not a desired size to approach. A coherent system may naturally require 5,000, 10,000 or more lines.

Count only implementation that materially participates in the claimed operational system. Do not satisfy scale with duplicated code, generated/vendor material, dead or unreachable modules, repeated boilerplate, unnecessary abstractions, copied thick templates, micro-module inflation or code whose removal would not materially change production behavior.

A production-style system should exhibit the characteristics appropriate to its domain, including where applicable:
- differentiated modules/components with distinct operational responsibilities;
- real runtime, build or operator entrypoints that reach the implementation;
- realistic state/data models and persistence boundaries;
- input/state validation and meaningful error handling;
- configuration and operational workflows;
- inter-component coupling where one subsystem's state or action materially affects another;
- restart/resume/recovery and partial-state handling;
- idempotency, fencing, deduplication or concurrency controls where the domain requires them;
- lifecycle, retention, reconciliation, publication/consumption or other domain-specific operational behavior;
- safe negative/failure behavior rather than happy-path-only logic.

Raw LOC, file count, module count or resource count never substitutes for these characteristics. If most of the code can be deleted while preserving the same operational behavior, the system is not substantively large.

## Behavioral breadth and edge/failure authenticity

Production systems have boundaries and failure paths. The task/verifier must include sufficient domain-relevant normal, edge, boundary, negative and failure-path behavior according to actual operational risk.

Examples include, where applicable: empty/partial/exhausted state, boundary values, repeated operations, restart/resume, malformed or unexpected data/state, unauthorized/forbidden operations, stale/fenced generations, rejected transitions, dependency/partial failures, cross-component combinations and safe recovery.

Negative/failure cases do not form a third test taxonomy. They are F2P when the starter behavior must change and P2P when correct rejection/safety behavior must be preserved.

Do not create edge/failure coverage by duplicating a happy-path test with different fixture values. Each such case must exercise a materially different invariant, operational boundary, rejection/safety semantic, recovery path or state transition.

For `large_system_strict`, the 25–30 F2P range must be reached organically from distinct operational requirements/states/transitions/failure modes/interactions. If complete behavioral analysis does not naturally support that range, choose a richer incident rather than manufacture tests.

## Stateful data scale

For `large_system_strict` tasks whose normal operation is data-backed, the inherited state must contain **10,000–20,000 primary business records** unless the controller records a domain-specific reason that this would be unrealistic.

The data must be deterministic and reproducible but materially varied. A production-style seed should contain meaningful variation across identities, historical cycles/runs, values, statuses, routes/types and other domain dimensions that affect reasoning.

Do not:
- present five or fifty homogeneous rows as a production database;
- duplicate the same fixture thousands of times;
- use nondeterministic random generation that changes verifier behavior;
- count generated data volume as authored code complexity.

## Business-logic depth

Major business-language modules must contain substantive reachable domain logic. A module count is not authentic when each program is only one `IF`, one constant `DISPLAY`, or one thin wrapper around a single comparison.

For COBOL-heavy `large_system_strict` tasks, each major callable program should normally show:
- input parsing and normalization;
- validation/error handling;
- multiple business/state branches;
- several procedure paragraphs or equivalent control sections;
- nontrivial use of the language such as `PERFORM`, `EVALUATE`, condition names/88-levels, `COMPUTE`, string/record handling, and functions where appropriate.

The exact syntax is not a quota. The gate measures whether the domain decision is genuinely represented rather than padded around one-line logic.

If a creator can delete most of a program and preserve the entire business decision, treat the program as thin business logic and revise the architecture rather than adding decorative statements.

### Portfolio diversity

Per-program depth is necessary but not sufficient. A creator must not take one large program skeleton, copy it across the portfolio, and change only `PROGRAM-ID`, field names, literals, or paragraph labels. That is the same scale-inflation defect as many one-line modules, just hidden inside larger files.

For COBOL-heavy strict tasks, run `.terminus/validate_business_module_diversity.py <task>` in addition to the per-program depth gate. It rejects logic-equivalent modules and blocks a portfolio when an overwhelming fraction shares the same paragraph-count/control-flow signature. Renaming paragraphs does not make a copied template distinct.

Common lifecycle conventions across programs are allowed. What must differ is the actual domain processing topology: the records inspected, validation stages, state classifications, calculations, business branches and failure handling should reflect each program's responsibility.

## Creator obligations

Scenario Researcher:
- identify what an operator actually saw and which artifacts would exist after that event;
- reject a “production” scenario that can only be explained by benchmark prose;
- reject a strict scenario whose production scale, F2P diversity or edge/failure surface can only be achieved through filler.

System Architect / Environment Builder:
- create the production evidence surface before instruction drafting;
- create representative deterministic starting state;
- keep major modules substantial, differentiated and runtime-reachable;
- implement credible production characteristics appropriate to the domain rather than building toward the LOC floor;
- reject both micro-program inflation and copied thick-template inflation.

Verifier Author:
- derive F2P/P2P cases from distinct operational behavior rather than numeric quotas;
- include sufficient edge/boundary/negative/failure behavior for the claimed operational risks;
- reject duplicate/parameter-renamed cases used to inflate the suite.

Human Writing Researcher / Instruction Writer:
- apply an **incident evidence test**: “Which solver-visible artifact supports each claimed incident fact?”
- do not invent fake dates, customer impact, host failures or operator actions merely to make prose sound human;
- prefer evidence + a short handoff over a compressed acceptance matrix.

Task Assembly / Complexity Governor:
- run `.terminus/validate_runtime_authenticity.py <task>`;
- run `.terminus/validate_business_module_diversity.py <task>` for declared business-language portfolios;
- treat >=3,000 substantive reachable LOC as a floor with no upper target;
- verify production characteristics, F2P organicity, and sufficient edge/negative/failure coverage;
- block thin business logic, duplicated/dead/unreachable scale, copied business-program templates, toy state, artificial test inflation, benchmark framing or missing incident evidence even when LOC/defect/test counts pass.

## Reviewer obligations

Task Architect, Originality & Authenticity Reviewer, Human Quality Reviewer and Comprehensive Reviewer must treat these as material authenticity defects:
- production incident asserted with no solver-visible evidence surface;
- toy-sized or homogeneous state presented as representative production data;
- a strict codebase constructed to sit near the 3,000-LOC floor rather than naturally representing the production architecture;
- many micro-programs/resources whose real decision logic is trivial and exists mainly to inflate scale;
- duplicated, dead, unreachable or unnecessary code/resources that materially inflate the measured system;
- many superficially large programs created from one repeated control-flow skeleton rather than distinct domain responsibilities;
- F2P cases split/renamed/parameter-duplicated primarily to reach the 25–30 range;
- insufficient domain-relevant edge/boundary/negative/failure-path coverage;
- solver-facing prose that describes the benchmark construction instead of the inherited operational problem.

These checks do not require a task to imitate any particular company. They require the claimed operational setting to be internally credible and evidenced.
