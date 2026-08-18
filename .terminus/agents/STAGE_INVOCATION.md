# Terminus Stage Invocation Contract

Stage-invocation policy version: `1.0`

This policy defines the executable handoff envelope used to invoke one registered Terminus stage/role pair. It compiles lifecycle, evidence-visibility, retrieval and acceptance contracts into a bounded machine-readable packet. It does not create a new lifecycle stage and does not change role authority.

Canonical implementation:

- `.terminus/execution/authority.py`
- `.terminus/execution/invocation.py`
- `.terminus/execution/cli.py`
- `.terminus/retrieval/policy.py`
- `.terminus/retrieval/stage_overlay.py`
- `.terminus/agents/stage_acceptance_predicates.json`
- `.terminus/agents/schemas/stage_invocation.schema.json`
- `.terminus/validate_stage_invocation.py`

## Core rule

A stage invocation is a projection of already-authoritative contracts:

`stage contract + canonical executable owner + exact task/control identity + evidence restrictions + declared inputs + optional authorized retrieval + status-specific acceptance predicates -> bounded invocation packet`

The packet is execution data, not semantic authority. It never contains hidden chain-of-thought, private scratchpad reasoning, or an inferred PASS.

## Input projection

The builder reads declared required/optional fields from `stage_contracts.json`. Only declared fields are projected. Undeclared supplied fields are dropped; only `ignored_input_count` remains. Missing required fields produce `BLOCKED_MISSING_INPUTS`; retrieval is skipped for that non-executable packet. Retrieval, chat memory or prior artifacts never fabricate a missing required input.

## Authority envelope

Every invocation records the stage ID, canonical executable role, owner/class, exact control-plane commit, task ID/task commit when task-scoped, packet/role/scope/CI bindings when applicable, evidence authorization and retrieval mode.

Task ID/task commit are a pair. For a **durable** lifecycle execution, the controller reserves the task ID and binds the input task commit before `RULE_RESOLUTION`; taskless packets are preview-only and cannot become durable execution records. The invocation task commit is the input snapshot. A producer/fixer that changes the task later reports the committed output snapshot in the result envelope.

The builder verifies referenced commits and refuses to label the loaded machine contracts as another control-plane commit. Any machine-readable overlay that changes the effective stage contract, including `.terminus/agents/human_writing_stage_overlay.json`, and the retrieval policy/overlay interpreter that applies it are part of that commit-bound snapshot and must match the declared `control_plane_commit` exactly.

## Execution authority versus retrieval audience

Retrieval/routing visibility does not grant aggregate-stage execution authority. Each registered aggregate stage has exactly one executable owner. Q4/Q6 remain independent reviewer evidence providers while CI Orchestrator owns the aggregate `QUALITY_INTERLOCK`; Stage-B/Comprehensive/Adjudicator evidence similarly feeds controller-owned `PRE_LLMAJ` rather than sharing its execution record.

## Mandatory exact reads

All declared stage policy/prompt files are returned in `mandatory_exact_reads` and must be read exactly. Similarity retrieval never substitutes for these files. The builder verifies the paths exist at the bound control-plane commit.

## Retrieval projection

Retrieval is optional and remains authorization-before-ranking. `INDEXED_CONTEXT`, `DIRECT_READ_FALLBACK`, `NOT_REQUESTED` and `SKIPPED_BLOCKED_INPUTS` are the only retrieval states. Retrieved context cannot widen authority or satisfy a missing required input automatically.

## Output contract projection

Every invocation includes:

- legal status values;
- required/optional outputs;
- persisted-artifact declarations;
- deterministic validators;
- semantic reviewers/evidence providers;
- required evidence description;
- failure routes and success transition;
- staleness triggers.

The stage owner returns one legal aggregate status and declared outputs. Reviewer roles use their own packet/result contracts rather than impersonating the aggregate owner.

## Acceptance predicate projection

The invocation also carries `acceptance_predicates`, copied from the exact control-plane snapshot in `.terminus/agents/stage_acceptance_predicates.json`.

These are **completion conditions, not new semantic authority**. They tell the aggregate owner exactly which already-owned facts/reviewer results must be represented before choosing an advancing status. Examples include Oracle=1/NOP=0 for deterministic validation and Q4/Q6 PASS with adequate confidence/evidence for `QUALITY_INTERLOCK_PASS`.

### Do

- inspect the predicate list for the status you intend to return;
- return a non-advancing status/route/block when a predicate is not satisfied;
- preserve the real reviewer/run evidence that the predicate references;
- report the committed output task snapshot separately in the result when an authorized producer/fixer changed task files.

### Do not

- treat predicate presence as permission to manufacture the required value;
- convert a reviewer `REVISE`, low confidence or insufficient evidence into aggregate PASS;
- choose PASS because all required output **keys** exist while their values violate the predicates;
- let a controller/reviewer mutate the task commit merely to satisfy a gate;
- remove or weaken a predicate inside the invocation packet.

The execution recorder enforces the authoritative registry independently of the packet, and workflow-state reconstruction rechecks it. Therefore tampering with this projection cannot create acceptance authority.

## Deterministic identity

`invocation_id` hashes the canonical packet, including the acceptance predicate projection, excluding only the ID itself and non-authoritative retrieval score magnitudes. A control-plane change to gate predicates therefore produces a different invocation identity.

## No hidden reasoning

No `chain_of_thought`, `reasoning`, `scratchpad` or equivalent private field exists. Persisted/exchanged material is limited to authority, evidence, declared inputs/outputs, predicates, routing and concise status/finding data.

## Failure behavior

Fail closed for unknown stage/role, wrong executable owner, unavailable or mismatched control-plane commit, missing exact-read file, incomplete task identity pair, stale declared policy version, unknown evidence restriction or unauthorized retrieval context. Ordinary missing stage inputs produce the explicit non-executable blocked packet instead of fabrication.

## Normal ChatGPT portability

A normal ChatGPT executor can consume or reconstruct the same packet through exact connected-GitHub reads. The local builder is the canonical machine implementation, not a dependency on Python/SQLite. The **single-owner rule** and acceptance conditions remain identical across execution surfaces.
