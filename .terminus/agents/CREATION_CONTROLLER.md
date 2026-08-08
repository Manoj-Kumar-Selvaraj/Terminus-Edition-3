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

For the strict large-system profile, a candidate that cannot naturally support the required footprint must return `SCENARIO_TOO_SMALL` rather than silently downgrade the profile.

### 2. System Architect

Defines the clean component/resource graph and operational boundaries before defects are injected.

For strict infrastructure tasks, the finished solver-visible system must contain **30–50 meaningful resources** whose relationships affect observable behavior. Repeated cosmetic resources do not count.

### 3. Defect Topology Designer

Creates the private causal defect graph before verifier implementation.

For `large_system_strict`:

- 20–30 observable defect manifestations;
- normally 4–8 root-cause clusters;
- at least 15 manifestations participating in causal/interdependency edges;
- multiple cross-cluster relationships;
- at least three plausible partial repairs that fix one layer while leaving the incident wrong.

The controller rejects one-independent-bug-per-test designs.

### 4. Environment Builder

Builds the solver-visible system and broken starter state without reading the final Oracle implementation.

For `large_system_strict`, require **>=3,000 substantive solver-visible code/config lines**, excluding tests, solution, docs, generated/vendor content, comments-only lines, blank lines and dead filler.

All counted code/config must be reachable from normal runtime/build/configuration/operator workflows or materially define those workflows.

### 5. Reference Solution Author

Implements the repair independently from hidden verifier bodies. The oracle restores approved operational invariants and cannot special-case known test fixtures.

### 6. Verifier Author

Builds behavioral tests from solver-visible requirements/contracts, not from the oracle implementation.

For `large_system_strict`:

- 25–30 F2P cases;
- P2P/regression cases according to risk;
- every F2P must empirically fail on starter/NOP and pass on Oracle;
- each case must be non-vacuous, independent and behavior-oriented;
- fixture renames do not count as distinct F2P cases.

The controller stores case classification in `.terminus/designs/<task>-test-map.json`; map classification must agree with the actual `test_f2p_*` / `test_p2p_*` functions.

### 7. Human Writing Researcher

Mandatory before the first `instruction.md` draft.

Uses real public engineering issue/incident/ticket sources across multiple ecosystems following the human-writing research policy and source corpus. It teaches information-selection patterns, not phrases, and stores per-task synthesis outside the task package.

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

For `large_system_strict` hard authoring constraints:

- substantive solver-visible LOC >= 3,000;
- infrastructure resources 30–50;
- defects 20–30;
- connected/interrelated manifestations >=15;
- F2P 25–30.

The automated gate must also reject structural padding: duplicate substantive environment files, duplicate defect manifestations, empty root-cause clusters, no cross-cluster causal interaction, untested requirements, test-map drift/misclassification and one requirement dominating the F2P suite.

Meeting the numbers does not certify difficulty. Adversarial checks still ask whether substantial code/resources/tests can be deleted without changing the operational system. Numeric success through padding is `REVISE` or `SCENARIO_TOO_SMALL`.

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

### `large_system_strict`

Default when the user asks for the large production-system profile. Numeric scale is a hard authoring constraint **in addition to** structural-authenticity checks. The official reviewer may still reject a large task that is clerical, synthetic, over-specified or uninteresting.

### `large_system`

Legacy diagnostic-scale profile. Use only when the controller records why the incident is inherently smaller and enforcing the strict scale would require filler. Numeric targets are warnings, but authenticity/coverage defects still block.

### Smaller profiles

A smaller task may be appropriate when the incident is inherently compact and still genuinely challenging. The controller records why the strict profile is inappropriate instead of padding the task.

## No-padding rules

Block creation when any of the following is used primarily to satisfy a number:

- dead code/modules;
- generated/vendor code counted as authored complexity;
- repeated infrastructure resources with no meaningful dependency/behavior difference;
- many independent typo-like bugs;
- duplicate verifier cases with changed fixture IDs;
- mislabeled F2P/P2P cases in the private map;
- unnecessary files never reached by runtime/workflow;
- documentation written only to inflate context;
- hidden requirements moved out of `instruction.md` merely to shorten it.

## Staleness

Any substantive change to scenario/contract, solver-visible environment, defect graph, oracle behavior, verifier mapping, instruction requirements or metadata explanations invalidates the affected producer evidence. Rerun the minimum affected producer roles and deterministic checks before returning to review.

## Handoff to independent review

`FROZEN_CANDIDATE` includes:

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
