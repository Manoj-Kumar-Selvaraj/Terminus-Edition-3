# Terminus Production Authenticity Policy

Policy version: `1.0`

This policy augments the Edition 3 creator and reviewer rules for tasks that claim to model an operational, production, stateful, or large-system incident. It is a local authoring gate, not a replacement for official Edition 3 acceptance rules.

## Production evidence surface

A production incident must leave solver-visible evidence. At least one incident log plus one independent operational artifact such as a shift handoff, persisted state snapshot, failed-run status, or operator note must support the incident described in `instruction.md`.

Do not invent a polished production story with no evidence in the environment. The instruction should point the solver to the evidence rather than restating every hidden acceptance condition.

Reject benchmark framing in solver/reviewer prose such as “cut-down reproduction”, “benchmark fixture”, “this package is used to reproduce”, or prose that explains why the task exists instead of what the operator observed.

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

## Creator obligations

Scenario Researcher:
- identify what an operator actually saw and which artifacts would exist after that event;
- reject a “production” scenario that can only be explained by benchmark prose.

System Architect / Environment Builder:
- create the production evidence surface before instruction drafting;
- create representative deterministic starting state;
- keep major business modules substantial and runtime-reachable.

Human Writing Researcher / Instruction Writer:
- apply an **incident evidence test**: “Which solver-visible artifact supports each claimed incident fact?”
- do not invent fake dates, customer impact, host failures or operator actions merely to make prose sound human;
- prefer evidence + a short handoff over a compressed acceptance matrix.

Task Assembly / Complexity Governor:
- run `.terminus/validate_runtime_authenticity.py <task>`;
- block thin business logic, toy state, benchmark framing or missing incident evidence even when LOC/defect/test counts pass.

## Reviewer obligations

Task Architect, Originality & Authenticity Reviewer, Human Quality Reviewer and Comprehensive Reviewer must treat these as material authenticity defects:
- production incident asserted with no solver-visible evidence surface;
- toy-sized or homogeneous state presented as representative production data;
- many micro-programs/resources whose real decision logic is trivial and exists mainly to inflate scale;
- solver-facing prose that describes the benchmark construction instead of the inherited operational problem.

These checks do not require a task to imitate any particular company. They require the claimed operational setting to be internally credible and evidenced.
