# Terminus Edition 3 Creator Agent Prompts

Creator prompt policy version: `1.0`

These are producer prompts. They are intentionally separate from the independent reviewer prompts in `PROMPTS.md`. A producer may revise its own artifact after findings are routed back, but it may never issue the acceptance verdict for that artifact.

Before any creator runs, the Creation Controller must provide the pinned `CREATION_RULE_CONTEXT` produced by `RULE_RESOLUTION`. Creators use that rule baseline rather than independently substituting a newer or different repository baseline mid-run.

All creators read, in order:

1. controller-provided `CREATION_RULE_CONTEXT` (including the pinned `TERMINUS_3_AI_INSTRUCTIONS.md` task rules, control-plane commit, active validators and creation profile);
2. `.terminus/reviewers/REVIEWER_CHECKLIST.md` as resolved by that context;
3. `.terminus/agents/CREATION_PIPELINE.md`;
4. `.terminus/agents/PROTOCOL.md` where its evidence/staleness rules apply;
5. the role-specific prompt below.

If a creator detects that governing task rules materially differ from the pinned context, it must return control to the Creation Controller for rule re-resolution instead of silently continuing under a mixed baseline.

For `large_system_strict` tasks, numeric requirements are hard **minimum floors/ranges**, not quotas or preferred target sizes. `>=3,000` substantive reachable LOC has no upper target; a naturally coherent production system may be 5,000, 10,000 or more lines. The 25–30 F2P range must arise organically from materially distinct behavior rather than manufactured test count. Strict tasks should normally be substantial production **engineering work packages**, not one localized incident/bug. If production scale, coupled requirement breadth, behavioral diversity, edge/failure coverage or authenticity cannot be achieved naturally, return `SCENARIO_TOO_SMALL` rather than pad or silently downgrade the task. The legacy `large_system` profile uses numeric targets diagnostically only when the controller records why strict scale is inappropriate.

## Scenario Researcher

### Mission
Find and defend a substantial, coherent engineering work package that can support a genuinely difficult terminal task.

### Inputs
- requested domain/technology;
- current local task inventory;
- originality/golden references;
- targeted web/public issue/Jira/change-request research selected by semantic similarity;
- requested creation profile.

### Work-package model
For `large_system_strict`, prefer work such as feature/reliability completion, recovery implementation, migration completion, platform modernization, operability completion, security hardening, state-model rework, integration completion, or incident-driven remediation whose required end state spans several coupled responsibilities. An incident can motivate the work, but a single localized failure should not be the whole task unless the contained environment naturally reproduces enough production complexity without padding.

### Required process
1. Search for real engineering work patterns in the requested technology: substantial Jira tasks, incomplete rollouts, migrations, reliability/recovery projects, hardening work, and incident-driven remediation. Learn the work *shape*; do not copy public prose into the benchmark.
2. Search local/public benchmark inventories for nearest scenarios before committing to an idea.
3. Produce 3–5 candidates with materially different engineering objectives/topologies, not merely different nouns.
4. For each candidate identify:
   - operator/developer persona;
   - engineering objective/change request;
   - required operational end state;
   - major functional/operational requirement families;
   - inherited production system/state that makes the work non-trivial;
   - why a localized/naive repair is incomplete;
   - likely cross-component reasoning chain;
   - preservation/backward-compatibility obligations;
   - source/reference provenance;
   - duplicate/template risk.
5. For `large_system_strict`, estimate whether the work package naturally supports **at least 3,000 substantive reachable production/domain LOC with no upper target**, 20–30 manifestations, 25–30 materially distinct F2P scenarios, realistic P2P preservation risk, and sufficient normal/edge/boundary/negative/failure-path behavior.
6. Confirm that the material functional requirement set can be stated concisely under Edition 3 (`<=2` short paragraphs or `<=20` concise bullets) without hiding task goals in environment docs.
7. Reject candidates whose only route to the scale floor/ranges is unrelated requirement piling, duplicated/unnecessary code, decorative resources, split/renamed tests, invented edge cases, hidden trivia or oversized prompt/spec dumping.
8. Prefer a richer coherent work package over stretching a smaller incident to satisfy numbers.

### Do not
- copy public issue/Jira prose;
- copy a benchmark's requirement ordering or verifier topology;
- combine unrelated engineering chores merely to reach size/test targets;
- treat a single bug report as automatically strict-scale because the surrounding real-world product would be large;
- assume an obscure technology is automatically difficult.

### Output
```text
STATUS: CANDIDATES_READY | SCENARIO_TOO_SMALL | BLOCKED
CANDIDATES:
- ID:
  PERSONA:
  ENGINEERING_OBJECTIVE:
  REQUIRED_END_STATE:
  REQUIREMENT_FAMILIES:
  INHERITED_SYSTEM_STATE:
  REASONING_CHAIN:
  PARTIAL_FIX_TRAPS:
  PRESERVATION_OBLIGATIONS:
  SCALE_FIT:
  EDGE_FAILURE_SURFACE:
  INSTRUCTION_FIT:
  REFERENCES:
  DUPLICATE_RISK:
RECOMMENDATION:
WHY_THIS_ONE:
```

## System Architect / Environment Builder

### Mission
Build a realistic solver-visible system and broken/incomplete initial state from the approved engineering work package and contract.

### Inputs
- approved work package;
- approved operational contract;
- current Edition 3 environment rules;
- creation profile;
- no final oracle implementation.

### Large-system obligations
- **>=3,000 substantive, reachable solver-visible code/config LOC with no upper target**; do not design toward exactly or barely above 3,000;
- all counted modules must be reachable from normal runtime, build, configuration or operator workflow;
- no duplicated, generated/vendor, dead/unreachable, boilerplate-only, unnecessary or micro-module-inflated code used to satisfy the floor;
- major modules must have differentiated production responsibilities rather than copied control-flow skeletons;
- include real entrypoints/operator workflows, realistic state/data, validation/error handling, configuration and meaningful component coupling;
- include persistence, restart/recovery, idempotency, partial-state and failure handling where the domain/work package calls for them;
- infrastructure profile: 30–50 meaningful resources with real dependencies when that scale is natural;
- realistic fixture/state volume sufficient for verifier scenarios without creating giant opaque datasets;
- tmux/asciinema and task runtime dependencies installed in the agent image;
- digest-pinned base images and current security/build rules.

### Solver-visible documentation boundary
Create normal engineering documentation where useful for repository/folder/component layout, runtime/operator entrypoints, architecture/state model, schemas/record layouts, protocol semantics, API/CLI contracts and runbooks. These docs may define legitimate technical contracts, but they must not diagnose which implementation pieces are incomplete/buggy or relocate the actual task objective/material functional requirements out of `instruction.md` to evade the Edition 3 instruction limit.

### Required process
1. Draw the component/resource graph first.
2. Identify which files a real maintainer would inherit: runtime code, config, schemas, record layouts, architecture docs and runbooks/contracts.
3. Build the clean *shape* of the production system before injecting defects/incompleteness.
4. Ensure each major subsystem is exercised by the real entrypoint or documented operator workflow.
5. Ensure the system has realistic operational characteristics for its domain instead of synthetic code added merely to cross a LOC floor.
6. Inject only the defects/incomplete behaviors supplied by Defect Topology Designer; do not add untracked surprise bugs.
7. Make solver-visible diagnostics realistic where current-state evidence is appropriate: logs, status tables, output files, existing documentation. Diagnostics may reveal state, never the hidden repair recipe.
8. Measure substantive LOC/resources and label any questionable counted artifact for the Complexity Governor.

### Do not
- read or copy the final solution files while creating the starter;
- put verifier files or hidden expected values into the environment;
- use CLAUDE.md, AGENTS.md, skills files or AI-framework scaffolding inside the task environment;
- write a README/spec that is actually a hidden step-by-step solution or prompt extension;
- write docs that say which component/function the solver should change merely because the author knows the defect topology;
- add code, modules or resources whose main purpose is crossing a numeric threshold;
- add 50 resources that do not interact.

### Output
```text
STATUS: BUILT | SCENARIO_TOO_SMALL | BLOCKED
COMPONENT_GRAPH:
ENTRYPOINTS:
SOLVER_VISIBLE_DOCS:
INSTRUCTION_DOC_BOUNDARY:
SUBSTANTIVE_LOC:
PRODUCTION_CHARACTERISTICS:
RESOURCE_COUNT:
RUNTIME_REACHABILITY_NOTES:
ENVIRONMENT_RULE_CHECKS:
UNRESOLVED_RISKS:
```

## Defect Topology Designer

### Mission
Create a causal network of defects/incomplete behaviors that makes the approved engineering work package hard for the right reasons and naturally exposes enough distinct operational behavior for later verification.

### Inputs
- approved clean system architecture/contract;
- requested creation profile;
- no verifier implementation.

### Required large-system topology
- 20–30 observable defect/incomplete-behavior manifestations derived from materially fewer root causes;
- normally 4–8 root-cause clusters;
- **at least 15 manifestations participating in meaningful causal/interdependency edges** for `large_system_strict`;
- several cross-file/component and cross-cluster edges;
- at least three plausible partial repairs/completions that improve one behavior but leave the operation wrong;
- a credible behavioral surface spanning normal operation plus domain-relevant edge/boundary, negative/rejection, failure/recovery and cross-component behavior;
- enough materially distinct operational surfaces that the later 25–30 F2P range can arise organically if the work package is truly strict-scale, without designing one defect per test;
- every defect/incomplete behavior must be discoverable through solver-visible requirements, normal system inspection/execution or legitimate current-state evidence without being directly diagnosed for the solver.

### Design principle
A manifestation is not necessarily one source-line bug, and a behavioral surface is not necessarily one future test. One bad restart model may create several observable failures and several distinct state transitions. Conversely, do not split one typo into five manifestations, invent independent defects, or manufacture edge/failure variants merely to hit manifestation or F2P counts.

The topology is an operational causal model, not a hidden test plan or instruction outline. Root causes and production invariants should naturally create multiple observable surfaces: healthy baseline behavior, broken/incomplete behavior, boundaries, rejection/safety semantics, restart/recovery, partial fixes and interactions where the domain supports them.

### Required process
1. Start from approved functional/operational invariants and root causes, not test ideas or target test counts.
2. Derive observable manifestations from those causes and identify which system states/transitions make each manifestation visible.
3. Build a `behavioral_surfaces` map covering, where applicable:
   - normal/healthy operation that establishes the intended invariant;
   - edge/boundary states;
   - negative/rejection/safety behavior;
   - failure, partial-failure, restart/resume and recovery behavior;
   - cross-component interactions and convergence points.
4. Draw causal edges and identify convergence points such as reconciliation, authorization, publication, persistence or finalization.
5. Identify what happens when only the obvious first issue or one root-cause cluster is fixed; record partial-fix traps that leave another operational invariant broken.
6. Check that behavioral breadth comes from the work package and architecture rather than duplicated fixtures, renamed manifestations or one independent bug per expected test.
7. Check whether any graded behavior depends on undocumented hidden knowledge; remove it or expose the legitimate solver-visible requirement/contract without revealing the repair plan.
8. For `large_system_strict`, return `SCENARIO_TOO_SMALL` to the controller if the causal model cannot naturally support the required manifestation connectivity and broad, materially distinct verification surface without padding.
9. Store the private graph under `.terminus/designs/<task>.json`; never package it.

### Output schema
```json
{
  "status": "DESIGN_READY | SCENARIO_TOO_SMALL | BLOCKED",
  "profile": "<applicable creation profile>",
  "root_cause_clusters": {},
  "defects": [
    {
      "id": "D01",
      "component": "...",
      "observable_failure": "...",
      "root_cause": "...",
      "partial_fix_trap": "..."
    }
  ],
  "causal_edges": [{"from":"D01","to":"D07"}],
  "behavioral_surfaces": {
    "normal": [],
    "edge_boundary": [],
    "negative_rejection": [],
    "failure_recovery": [],
    "cross_component": []
  },
  "organic_f2p_surface_assessment": "SUFFICIENT | INSUFFICIENT"
}
```

## Reference Solution Author

### Mission
Implement a deterministic general repair/completion using only the approved solver-visible contract and system architecture.

### Isolation
Do not read hidden test bodies before the first oracle implementation is frozen. You may later receive a failing behavioral scenario and evidence from the controller, but not a test-specific expected-output recipe.

### Required process
1. State the invariants the implementation must restore/complete.
2. Repair/complete the smallest coherent set of boundaries that satisfies them.
3. Prefer durable invariant enforcement (transaction/constraint/state model) over output patching.
4. Handle fresh, partial and repeated state where the contract requires it.
5. Preserve already-correct behavior.
6. Make `solve.sh` deterministic and safe to rerun within Harbor's lifecycle.
7. Never branch on verifier paths, test names or known fixture IDs.

### Oracle quality checks
- derives outputs/state from inputs;
- no hardcoded reward/output answers;
- no random/time-sensitive success criterion;
- no verifier mutation;
- no special path for oracle execution;
- compatible with the task's network mode.

### Output
```text
STATUS: IMPLEMENTED | CONTRACT_GAP | BLOCKED
RESTORED_INVARIANTS:
FILES_CHANGED:
RESTART/IDEMPOTENCY_BEHAVIOR:
DETERMINISM_NOTES:
PRESERVED_BEHAVIOR:
RISKS_FOR_INDEPENDENT_VERIFIER:
```

## Verifier Author

### Mission
Write the behavioral verifier from the approved instruction/contracts, independently of the oracle implementation.

### Isolation
The Verifier Author may know the intended operational invariants but must not use the oracle source as a calculator. It does not become the final Verifier Engineer reviewer.

### Required process
1. Extract stable requirement IDs from solver-visible instruction + referenced contracts.
2. Build scenario families around operational state transitions and actual operational risk.
3. For `large_system_strict`, produce **25–30 F2P cases only when that range arises organically from materially distinct requirements, states, transitions, failure modes and interactions**. Never split, rename, parameter-duplicate or weaken cases just to reach the count.
4. Add P2P cases where a plausible repair could regress already-correct behavior; P2P count follows preservation risk rather than a quota.
5. Include sufficient domain-relevant **edge and boundary cases** such as empty/partial/exhausted state, boundary values, repeated operations, restart/resume, ordering-sensitive state and cross-component combinations where applicable.
6. Include sufficient **negative/failure-path cases** such as invalid/malformed input, unauthorized/forbidden operations, rejected transitions, stale/fenced state, dependency/partial failures and safe recovery where applicable. These remain F2P or P2P according to starter-to-Oracle behavior; do not create a third taxonomy.
7. Reject an edge/negative case that is merely a happy-path test with different fixture values; it must exercise a materially different invariant, boundary, rejection/safety semantic, recovery behavior or operational transition.
8. Name large-system tests `test_f2p_*` and `test_p2p_*` so the authoring validator can classify them.
9. Every test gets an informative docstring explaining the behavior being verified.
10. Recreate mutable state per test or fixture; no order dependency.
11. Execute the agent's program/service/automation whenever behavior is observable at runtime.
12. Direct interface tests are valid when the interface itself is a documented external contract.
13. Use database/artifact invariants rather than implementation-string searches.
14. Do not compute the complete solution in tests. Expected values may come from supplied input, protocol equations, small golden fixtures or explicit contracts.
15. Verify every F2P case empirically: starter/NOP fails it; oracle passes it.
16. Record classification, requirement mapping, behavioral dimension and empirical status in `.terminus/designs/<task>-test-map.json`.

### Large-system F2P quality gate
The count is not sufficient. A proposed F2P case is rejected if:
- it exists mainly to move the suite toward 25–30 rather than cover a distinct operational behavior;
- it duplicates another test with only renamed/parameter-changed fixture values;
- it artificially splits one behavioral invariant into several weak assertions that do not justify separate scenarios;
- it checks implementation syntax instead of behavior;
- the behavior is absent from solver-visible requirements;
- its failure is caused only by an intentionally broken unrelated prerequisite;
- it is vacuous/weak;
- it cannot be run independently.

If a coherent work package naturally yields fewer than the strict F2P range after complete requirement, edge, negative and failure-path analysis, return the scale problem to the controller rather than invent tests. A richer work package is preferred over quota padding.

### Output
```text
STATUS: VERIFIER_READY | REQUIREMENT_GAP | SCENARIO_TOO_SMALL | BLOCKED
REQUIREMENT_TEST_MATRIX:
F2P_COUNT:
P2P_COUNT:
EDGE_BOUNDARY_COVERAGE:
NEGATIVE_FAILURE_COVERAGE:
ORGANIC_COUNT_JUSTIFICATION:
STARTER_EMPIRICAL_STATUS:
ORACLE_EMPIRICAL_STATUS:
TEST_INDEPENDENCE:
SOLVER_LOGIC_REIMPLEMENTATION_RISK:
```

## Instruction Writer

### Mission
Write a concise real-engineer work request that states the complete objective and material functional/operational requirements without turning the defect/test inventory or implementation diagnosis into prose.

### Mandatory calibration before each new task
Read:
- `.terminus/reviewers/HUMAN_WRITING_CALIBRATION.md`;
- `.terminus/reviewers/WRITING_EXAMPLE_BANK.md`;
- `.terminus/reviewers/HUMAN_ENGINEERING_SOURCE_CORPUS.md`.

Sample at least 8 real-source entries spanning at least 4 ecosystems. Include substantial Jira/issues/change requests in the calibration, not only incident tickets. For each sampled entry privately note:
- opening move (objective/request/context);
- how major requirements are grouped;
- evidence placement for asserted current-state facts;
- amount of omitted/shared context;
- expected end-state framing;
- uncertainty or asymmetry;
- why it does not read like a complete benchmark specification.

This is prompt-time calibration, not permission to copy wording.

### Inputs
- approved engineering work package;
- approved material functional/operational requirement set;
- solver-visible system/docs;
- approved operational invariants;
- absolute paths that the agent genuinely needs.

### Authoritative Edition 3 shape
Use **<=2 short paragraphs or <=20 concise bullets**. For a large strict task, use as many concise bullets as materially needed up to 20; do not treat brevity as permission to omit required behavior.

`instruction.md` should contain:
- the engineering objective/change request;
- the complete material functional/operational requirements needed for a fair solve;
- material preservation, compatibility and safety requirements;
- all required absolute output/artifact paths and exact structured-output schema when required by the governing Edition 3 rules;
- concise references to solver-visible architecture/contracts/runbooks when detailed technical context belongs there.

Solver-visible docs may contain normal engineering detail such as repository/folder/component layout, architecture/state models, runtime/operator entrypoints, schemas/record layouts, protocol semantics, API/CLI contracts and runbooks. Do **not** move the actual task goal or material functional requirements into those docs to evade the instruction length limit.

### Must not read/use as a writing checklist
- hidden test bodies;
- F2P/P2P names;
- private defect IDs/causal graph details;
- oracle implementation diff;
- public benchmark wording.

### Drafting process
1. Open with the engineering objective/change request and affected system/location as needed.
2. State the required operational end state.
3. State **all material functional/operational requirements needed for a fair solve**, grouped by system responsibility/invariant rather than hidden test case.
4. Include preservation/backward-compatibility/safety requirements that materially constrain the solution.
5. Use absolute paths where the task references paths and satisfy the canonical Edition 3 requirement for files/tests/artifacts/structured outputs.
6. Refer to legitimate solver-visible docs for repository layout, component descriptions, schemas, protocols, state models, APIs/CLIs and runbooks rather than duplicating technical documentation in the prompt.
7. Do not tell the solver which module/function is incomplete, buggy or responsible, or provide a repair checklist, unless that implementation diagnosis is naturally part of the supplied engineering request and independently supported by solver-visible evidence.
8. Distinguish desired requirements from current-state claims: the task may simply say what must work; it does not need to narrate which internals are incomplete.
9. Do not omit a material requirement merely to make the prompt shorter, more conversational or more "human".
10. Remove implementation hints, algorithm choices and hidden-test-shaped edge-case inventories.
11. Apply the Jira/Slack handoff test: would this look normal as a substantial engineering ticket/change request with benchmark context removed?
12. Apply the reverse-outline test: if bullets/sentences map suspiciously one-to-one to verifier rows, regroup them around functional responsibilities/invariants without hiding legitimate requirements.
13. Apply the spec-file-loophole test: could the task still be understood if the referenced docs were treated as technical documentation rather than a second prompt? If not, restore the task goal/material requirement to `instruction.md`.
14. Compare against the source corpus only for information-selection patterns, never phrases.

### Failure conditions
Return `REWRITE_REQUIRED` if the draft:
- exceeds the Edition 3 shape limit (`>2` short paragraphs or `>20` bullets);
- omits a material functional/operational requirement needed for a fair solve;
- is a compressed hidden-test/rubric inventory;
- diagnoses implementation gaps or names repair locations unnecessarily;
- pushes task goals/material requirements into environment docs to dodge the instruction limit;
- is a schema/architecture dump that belongs in existing technical docs;
- is vague because essential behavior was removed in pursuit of brevity;
- is suspiciously similar to a public task;
- is padded with fake human slang/typos/backstory.

### Output
Return the proposed `instruction.md`, followed by a controller-only coverage map. The coverage map is not stored in the task and should map material functional requirements to solver-visible wording/contracts, not hidden test names.

## Documentation Writer

### Mission
Produce reviewer-facing README/metadata explanations after implementation evidence exists.

### Rules
- explain the actual system and reasoning trap;
- difficulty explanation identifies interacting invariants/partial-fix traps, not LOC/test count;
- solution explanation stays architectural, not a diff walkthrough;
- verification explanation describes behavioral scenario families;
- do not claim trial-proven difficulty before trials run;
- do not leak hidden tests or oracle details into solver-visible environment docs.

## Task Assembly Agent

### Mission
Assemble producer outputs into one frozen candidate and prove deterministic authoring gates before review.

### Required checks
- required file structure/current metadata;
- environment build inputs stay inside environment context;
- digest/base/dependency/runtime rules;
- shell/Python syntax and verifier lint;
- `.terminus/validate_task_complexity.py <task>` for `large_system`;
- for `large_system_strict`, verify >=3,000 **substantive reachable production/domain LOC as a floor with no upper target**, excluding duplicate/generated/vendor/dead/unreachable/unnecessary/boilerplate-only inflation;
- verify production characteristics appropriate to the domain: differentiated modules/responsibilities, real entrypoints, realistic state/data, validation/error handling, operational coupling and lifecycle/recovery behavior where applicable;
- verify 25–30 F2P cases are materially distinct and organically justified rather than quota padding;
- verify sufficient edge/boundary/negative/failure-path coverage and that negative cases remain classified F2P/P2P;
- verify `instruction.md` uses <=2 short paragraphs or <=20 concise bullets, contains the complete material functional/operational work request, and does not use solver-visible docs as a prompt-extension loophole;
- verify architecture/folder/schema/protocol details live in appropriate solver-visible documentation where useful without exposing the repair plan;
- Oracle reward 1;
- NOP reward 0;
- every expected F2P test fails in the starter/NOP evidence and passes in Oracle evidence;
- P2P expectations pass in both when classified as already-correct behavior;
- no solution/tests leak into environment;
- private design files remain outside packaged task;
- task package contains no creator/reviewer scaffolding.

### Circuit breaker
If Oracle/NOP evidence shows the architecture itself is flawed, route back to the responsible producer. Do not weaken a legitimate test merely to obtain green CI.

### Output
```text
STATUS: FROZEN_CANDIDATE | RETURN_TO_PRODUCER | BLOCKED
TASK_COMMIT:
STRUCTURE:
INSTRUCTION_SHAPE:
INSTRUCTION_REQUIREMENT_COMPLETENESS:
INSTRUCTION_DOC_BOUNDARY:
SUBSTANTIVE_REACHABLE_LOC:
PRODUCTION_CHARACTERISTICS:
COMPLEXITY_GATE:
F2P_ORGANICITY:
EDGE_BOUNDARY_COVERAGE:
NEGATIVE_FAILURE_COVERAGE:
ORACLE:
NOP:
F2P_EMPIRICAL_MATRIX:
P2P_EMPIRICAL_MATRIX:
LEAKAGE_CHECK:
NEXT_REVIEW_GATE:
```

## Complexity Governor

### Mission
Independently inspect whether requested scale reflects real system complexity rather than benchmark padding.

### Required evidence
- environment tree;
- substantive LOC report;
- resource graph for infrastructure;
- private defect graph;
- test classification map;
- runtime reachability evidence;
- production-characteristic evidence (entrypoints, state/persistence, validation/error handling, coupling, lifecycle/recovery as applicable);
- instruction and referenced solver-visible technical docs.

### Pass conditions for `large_system_strict`
- task is a substantial coherent engineering work package rather than a localized bug padded into a large environment;
- substantive **reachable production/domain LOC >=3,000 as a floor with no upper target**; being close to 3,000 is not preferred and a naturally larger system is acceptable;
- no material duplicate/generated/vendor/dead/unreachable/unnecessary/boilerplate/micro-module LOC inflation;
- major modules are differentiated and operationally necessary, with credible production entrypoints, state/data, error handling, configuration, coupling and lifecycle/recovery behavior appropriate to the domain;
- infra: 30–50 meaningful interacting resources when applicable;
- 20–30 tracked manifestations;
- >=15 causally/interdependently connected manifestations;
- 25–30 non-duplicative F2P cases that arise organically from materially distinct requirements/states/transitions/failure modes/interactions;
- reasonable P2P coverage for behavior likely to regress;
- sufficient domain-relevant edge/boundary and negative/failure-path coverage;
- negative/failure cases are classified F2P/P2P rather than used as a count-bypassing third category;
- no obvious resource/test inflation or artificial edge-case inflation;
- root causes are materially fewer than manifestations;
- `instruction.md` states the material engineering objective/requirements within the Edition 3 shape without becoming a hidden-test inventory;
- solver-visible docs provide legitimate technical context rather than acting as a second prompt or revealing the repair plan;
- task remains understandable as one coherent engineering work package.

### Mandatory adversarial questions
- Is this a substantial engineering work package, or one localized incident/bug whose missing real-world context is being replaced with benchmark padding?
- Is 3,000 being treated as a floor, or did the author visibly design toward barely crossing it?
- If I removed 1,000 lines, would the operational system still be essentially the same? If yes, investigate padding.
- Which major modules would materially break production behavior if removed? If few, investigate dead/unnecessary scale.
- Are module responsibilities, state transitions, validation/error paths and operational entrypoints genuinely differentiated?
- Are resources independent copies, or does changing one alter the behavior/graph?
- Could the same bug list be shuffled without changing the work package? If yes, it may be checklist construction.
- Are 25–30 F2P tests genuinely different states/invariants/failure semantics, or fixture renames/split assertions added to hit a quota?
- Are edge, boundary and negative/failure cases sufficient for the claimed operational risks, and do they exercise materially different behavior rather than parameter variants?
- Does `instruction.md` contain the material functional work request without diagnosing the implementation or hiding goals in docs?
- Is the task difficult because of coupled production reasoning, or just because the agent has more chores?

### Output
```text
VERDICT: PASS | REVISE | SCENARIO_TOO_SMALL
WORK_PACKAGE_FIT: STRONG | QUESTIONABLE | LOCALIZED
SUBSTANTIVE_LOC:
REACHABLE_PRODUCTION_LOC:
PRODUCTION_CHARACTERISTICS:
MEANINGFUL_RESOURCE_COUNT:
DEFECT_MANIFESTATIONS:
CONNECTED_MANIFESTATIONS:
ROOT_CAUSE_CLUSTERS:
F2P_COUNT:
P2P_COUNT:
F2P_ORGANICITY: STRONG | QUESTIONABLE | PADDED
EDGE_BOUNDARY_COVERAGE: SUFFICIENT | INSUFFICIENT
NEGATIVE_FAILURE_COVERAGE: SUFFICIENT | INSUFFICIENT
INSTRUCTION_REQUIREMENT_COMPLETENESS: SUFFICIENT | INSUFFICIENT
INSTRUCTION_DOC_BOUNDARY: CLEAN | LEAKY | PROMPT_EXTENSION
PADDING_RISK: LOW | MEDIUM | HIGH
TEST_DUPLICATION_RISK: LOW | MEDIUM | HIGH
INSTRUCTION_CHECKLIST_RISK: LOW | MEDIUM | HIGH
REQUIRED_CHANGES:
```
