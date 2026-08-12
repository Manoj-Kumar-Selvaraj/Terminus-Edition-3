# Terminus Edition 3 Instruction Policy

Instruction policy version: `1.0`

This file is the authoritative detailed policy for authoring, repairing and reviewing solver-visible `instruction.md` content. `TERMINUS_3_AI_INSTRUCTIONS.md` remains the repository-wide Edition 3 task-rule source. `.terminus/AGENT_SYSTEM.md` owns the system-level invariant and routing model; this file specializes that invariant for instruction work.

This policy is consumed by the Instruction Writer, Instruction Reviewer, Q1 Spec Gap Repairer, Q3 Spec Ambiguity Repairer, Q4 Spec-Test Contract Reviewer, Human Quality Reviewer and Comprehensive Reviewer. Role-specific prompt files may narrow execution details, but they must not contradict this policy.

## Core rule

`instruction.md` is a concise engineering work request, not a compressed hidden-test inventory and not an implementation diagnosis.

Edition 3 allows **<=2 short paragraphs or <=20 concise bullets**. For a `large_system_strict` task, use as many concise bullets as materially needed up to 20. Brevity must never cause omission of a material requirement needed for a fair solve.

A substantial task may therefore contain a substantial chain of functional requirements. The problem is not the number of legitimate requirements; the problem is hidden-test-shaped enumeration, repair guidance, or displaced task goals hidden in technical documentation.

## Required instruction content

The writer should normally state, as applicable:

- the engineering objective/change request;
- the affected system/location when needed for orientation;
- the required operational end state;
- all material functional and operational requirements needed for a fair solve;
- material preservation, compatibility and regression requirements;
- material safety, rejection and failure-handling requirements when they are part of the requested behavior;
- required absolute output/artifact paths;
- exact structured-output schema, fields, types and ordering rules when governing Edition 3 rules require a structured output;
- concise references to solver-visible technical documentation needed to understand the inherited system or detailed technical contract.

Do not omit a material requirement merely to make the handoff shorter or more conversational. Human engineering prose can be concise while still being complete at the functional-contract level.

## Instruction versus solver-visible documentation

Use this boundary:

`instruction = what must work -> docs/contracts = how the inherited system is organized/governed -> code/runtime = what exists now -> solver = identify implementation gaps and repair/complete them`

`instruction.md` owns the actual engineering ask and its material functional/operational requirements.

Solver-visible documentation may contain normal engineering material such as:

- repository, folder and component layout;
- architecture and state models;
- runtime/build/operator entrypoints;
- schemas and record layouts;
- protocol semantics;
- API and CLI contracts;
- configuration/reference material;
- runbooks and operator procedures that would legitimately exist with the inherited system.

Solver-visible docs must **not** become a second prompt used to hide the actual task goal, material functional requirements, acceptance checklist or repair plan merely to evade the instruction length limit.

A technical contract may legitimately define detailed protocol/schema semantics that would be unnatural to restate in a Jira ticket. That does not permit relocating the engineering objective or requirement set into a pseudo-spec prompt extension.

## Implementation-diagnosis boundary

State required end-state behavior; do not normally tell the solver which internal module, function, branch, query, resource or implementation mechanism is incomplete, buggy or responsible.

An implementation diagnosis may appear only when both are true:

1. that diagnosis would naturally be part of the supplied engineering handoff rather than knowledge available only to the task author/verifier; and
2. it is independently supported by solver-visible evidence or a legitimate existing technical artifact.

Do not use private defect topology, Oracle diffs, hidden test names, verifier assertion order or creator knowledge as a source of solver-facing diagnosis.

## Current-state claims and evidence

Desired requirements are not incident claims and do not require synthetic evidence. For example, “replay must be idempotent across restart” is a requested behavior, not a claim that a particular outage occurred.

When `instruction.md` asserts a concrete current condition or event—such as a failed migration, observed production state, specific operator symptom, existing compatibility condition or recorded partial rollout—the writer must be able to identify the solver-visible evidence supporting that claim when such evidence would naturally exist.

Do not invent dates, customers, outages, host failures, operator actions, business impact or other backstory merely to make the task sound human.

## Human engineering tests

Instruction Writer, Instruction Reviewer, Q1 and Q4 apply these tests; Q3 applies them when its clarification changes solver-facing prose.

### Jira/Slack handoff test

Would the text look normal as a substantial engineering ticket/change request with benchmark context removed?

A large Jira-style task may legitimately list many coupled functional requirements. It should still read as a coherent work package rather than a grading rubric.

### Requirement-completeness test

Are all material functional/operational requirements needed for a fair solve present in `instruction.md` or legitimately discoverable from referenced technical contracts without hiding the actual task goal in docs?

Do not convert “humanization” into artificial omission.

### Reverse-outline test

If bullets/sentences map suspiciously one-to-one to verifier/rubric rows, regroup them around meaningful system responsibilities, operational invariants or functional requirement families without deleting legitimate requirements.

One functional requirement may naturally support several verifier scenarios. Conversely, several genuinely distinct functional requirements should not be collapsed into one vague sentence merely to hide test topology.

### Spec-file-loophole test

Do referenced docs remain ordinary technical documentation, or have they become a second instruction file, acceptance checklist or repair map?

A failure includes moving material task goals into `/app/docs/...` only so `instruction.md` remains artificially short.

### Current-state evidence test

Only when the instruction asserts current conditions/events, identify the solver-visible evidence supporting those claims. Desired end-state requirements are not current-state claims.

## Hidden-test and repair leakage prohibitions

Do not expose:

- hidden test names or numbering;
- private defect IDs;
- hidden fixture families/values unless the value is itself a legitimate public contract value;
- assertion ordering;
- Oracle implementation details;
- one-bullet-per-test acceptance inventories;
- detection guidance that names each hidden bug class;
- implementation steps, exact repair recipes or preferred internal design when multiple conforming implementations are allowed.

The solver-visible requirement surface must be sufficient to make grading fair, but difficulty should come from understanding and completing the inherited system rather than from reading the verifier translated into prose.

## Output and artifact requirements

Where the task requires solver-produced files/artifacts, `instruction.md` must follow the current Edition 3 task rules for naming every verifier-consumed path. Use absolute paths.

Where a structured output is required, the exact externally graded schema belongs in solver-visible material. Prefer `instruction.md` for compact schemas that are central to the requested deliverable; a referenced technical contract is appropriate when the schema is substantial and would naturally exist as system documentation. In either case, the requirement must remain clearly discoverable from the instruction.

## Role ownership

- **Instruction Writer** — produces/revises `instruction.md` under this policy.
- **Q1 Spec Gap Repairer** — repairs legitimate verifier->spec gaps without hidden-test leakage or spec-file loopholes.
- **Q3 Spec Ambiguity Repairer** — clarifies grading-relevant ambiguity while preserving the instruction/docs boundary and implementation freedom.
- **Instruction Reviewer** — cold semantic review of completeness, fairness, concision, naturalness and leakage.
- **Q4 Spec-Test Contract Reviewer** — independently verifies bidirectional requirement/test alignment plus instruction completeness and documentation-boundary integrity.
- **Human Quality Reviewer** — checks final solver-facing prose for synthetic/benchmark-shaped writing and unsupported claims.
- **Comprehensive Reviewer** — breadth backstop across the current instruction-related criterion registry.

## Structured processing contract

The canonical stage metadata, expected inputs/outputs, validators/reviewers, failure routes and staleness triggers for instruction work are defined by stage `INSTRUCTION_DRAFT` and related alignment/review stages in `.terminus/agents/stage_contracts.json`.

Role prompts should consume the stage contract and this policy rather than restating this entire document at runtime. Runtime projection should include only the fields and policy excerpts required by the role.

## Failure routing

- missing material solver-visible requirement -> Q1 Spec Gap Repairer;
- material solver-visible requirement not meaningfully tested -> Q2 Verifier Coverage Repairer;
- grading-relevant ambiguity -> Q3 Spec Ambiguity Repairer;
- hidden-test-shaped writing, prompt-extension docs or unnecessary implementation diagnosis -> Instruction Writer repair, then independent Instruction Reviewer/Q4 re-review as applicable;
- material verifier/spec conflict after producer-side alignment -> Q4, then Adjudicator under the normal circuit-breaker rules when required;
- deterministic task-format/path/schema violation -> Q7 Task Format Enforcer when within Q7's decision right.
