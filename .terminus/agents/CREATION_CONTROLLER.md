# Terminus Edition 3 Creation Controller

Policy version: `1.0`

This controller is the mandatory producer-side pipeline for new tasks. It ends at `FROZEN_CANDIDATE`; independent review begins only after that point.

Authoritative Edition 3 rules, `.terminus/reviewers/REVIEWER_CHECKLIST.md`, and current validator behavior override this file if they conflict.

## Creation states

`IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> DOCUMENTATION_DRAFT -> ASSEMBLY -> COMPLEXITY_GATE -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE`

`BLOCKED` overlays any state when evidence, scope, rules or tooling prevent safe continuation.

## Mandatory role sequence

### 1. Scenario Researcher

Produces 3–5 candidate incidents and originality/provenance evidence. Select one only when it is realistic, coherent and large enough for the requested profile without padding.

For `large_system`, a candidate that cannot naturally support the substantive system footprint must return `SCENARIO_TOO_SMALL`.

### 2. System Architect

Defines the clean component/resource graph and operational boundaries before defects are injected.

For infrastructure, target **30–50 meaningful resources** only when that scale is natural to the incident. Resource count alone is never difficulty evidence.

### 3. Defect Topology Designer

Creates the private causal defect graph before verifier implementation.

For `large_system`:

- 20–30 observable defect manifestations;
- normally 4–8 root-cause clusters;
- at least 10 causally connected manifestations;
- 15+ connected manifestations preferred;
- at least three plausible partial repairs that fix one layer but leave the incident wrong.

The controller rejects one-independent-bug-per-test designs.

### 4. Environment Builder

Builds the solver-visible system and broken starter state without reading the final oracle implementation.

For `large_system`, require **>=3,000 substantive solver-visible code/config lines**, excluding tests, solution, docs, generated/vendor content, comments-only lines, blank lines and dead filler.

All counted code/config must be reachable from normal runtime/build/configuration/operator workflows or materially define those workflows.

### 5. Reference Solution Author

Implements the repair independently from hidden verifier bodies. The oracle restores approved operational invariants and cannot special-case known test fixtures.

### 6. Verifier Author

Builds behavioral tests from solver-visible requirements/contracts, not from the oracle implementation.

For `large_system`:

- 25–30 F2P cases;
- P2P/regression cases according to risk;
- every F2P must empirically fail on starter/NOP and pass on oracle;
- each case must be non-vacuous, independent and behavior-oriented;
- fixture renames do not count as distinct F2P cases.

The controller stores empirical case classification in `.terminus/designs/<task>-test-map.json`.

### 7. Human Writing Researcher

Mandatory before the first `instruction.md` draft.

Retrieves and synthesizes 20–40 real public human engineering artifacts across at least four repositories/ecosystems, following `.terminus/agents/HUMAN_WRITING_RESEARCHER.md`.

It teaches information-selection patterns, not phrases. Output is stored outside the task package at `.terminus/research/<task>-human-writing.md`.

Required outcome: `CALIBRATION_READY`.

### 8. Instruction Writer

Receives the approved incident, solver-visible contracts, required absolute paths and Human Writing Researcher synthesis.

It does **not** receive hidden test bodies, oracle diffs, private defect IDs or a sentence checklist generated from the verifier.

Draft must pass the Jira/Slack handoff and reverse-outline self-checks before assembly.

### 9. Documentation Writer

Produces reviewer-facing README/metadata explanations after implementation behavior is known. It must not turn environment documentation into a hidden solution guide.

### 10. Task Assembly Agent

Assembles the candidate, validates required structure, classifies F2P/P2P, checks leakage, syntax/lint and creator evidence consistency.

### 11. Complexity Governor

Runs both automated and adversarial checks.

For `large_system` automated floors:

- substantive solver-visible LOC >= 3,000;
- infra resources 30–50 when `task_kind=infrastructure`;
- defects 20–30;
- connected manifestations >=10;
- F2P 25–30.

Adversarial checks determine whether these numbers reflect real complexity or filler. A candidate that meets numbers through padding is `REVISE` or `SCENARIO_TOO_SMALL`.

### 12. Deterministic Validation

Before independent review:

- static/preflight clean;
- verifier lint clean;
- complexity gate clean;
- Oracle reward = 1;
- NOP reward = 0;
- all planned F2P cases empirically Oracle-pass / starter-fail;
- intended P2P cases preserve starter behavior;
- no solution/test leakage;
- no creator/reviewer scaffolding in package.

Only then freeze the candidate.

## Creation profile registry

### `large_system`

Use by default for tasks explicitly requested to represent a sizeable production system.

Numeric floors are **authoring constraints**, not Edition 3 acceptance substitutes. The official reviewer can still reject a task that is large but clerical, over-specified, synthetic or uninteresting.

### Smaller profiles

A smaller task may be appropriate when the incident is inherently compact and still genuinely challenging. The controller must record why the large profile is inappropriate instead of padding the task.

## No-padding rules

The controller must block creation when any of the following is used primarily to satisfy a number:

- dead code/modules;
- generated/vendor code counted as authored complexity;
- repeated infrastructure resources with no meaningful dependency/behavior difference;
- many independent typo-like bugs;
- duplicate verifier cases with changed fixture IDs;
- unnecessary files never reached by runtime/workflow;
- documentation written only to inflate context;
- hidden requirements moved out of `instruction.md` merely to shorten it.

## Staleness

Any substantive change to the following invalidates downstream producer evidence:

- scenario/operational contract;
- solver-visible environment architecture;
- defect graph;
- oracle behavior;
- verifier requirement mapping;
- instruction requirements;
- metadata difficulty/solution/verification explanations.

After a material task change, rerun the minimum affected producer roles and deterministic evidence before returning to review.

## Handoff to independent review

`FROZEN_CANDIDATE` must include:

```text
TASK:
TASK_COMMIT:
CREATION_PROFILE:
SCENARIO_RESEARCH: READY
DEFECT_GRAPH: READY
SUBSTANTIVE_LOC:
MEANINGFUL_RESOURCE_COUNT:
DEFECT_MANIFESTATIONS:
CONNECTED_MANIFESTATIONS:
F2P_COUNT:
P2P_COUNT:
HUMAN_WRITING_CALIBRATION: READY
ORACLE: 1
NOP: 0
F2P_EMPIRICAL_MATRIX: COMPLETE
LEAKAGE_CHECK: PASS
COMPLEXITY_GATE: PASS
```

The reviewer system receives the frozen task and evidence but not producer self-approval. Writers/builders cannot mark the task accepted.
