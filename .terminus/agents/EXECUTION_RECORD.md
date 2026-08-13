# Terminus Execution Record and Transition Contract

Execution-record policy version: `1.0`

This policy defines how one completed stage invocation is converted into a durable, machine-readable execution record and a deterministic transition decision. It consumes the bounded invocation produced under `.terminus/agents/STAGE_INVOCATION.md`; it does not create new role authority, infer missing evidence, or replace the semantic reviewer that owns a judgment.

Canonical implementation:

- `.terminus/agents/execution_outcomes.json`
- `.terminus/agents/stage_acceptance_predicates.json`
- `.terminus/agents/schemas/execution_outcomes.schema.json`
- `.terminus/agents/schemas/stage_acceptance_predicates.schema.json`
- `.terminus/agents/schemas/stage_result.schema.json`
- `.terminus/agents/schemas/execution_record.schema.json`
- `.terminus/execution/authority.py`
- `.terminus/execution/acceptance.py`
- `.terminus/execution/record.py`
- `.terminus/execution/result_cli.py`
- `.terminus/validate_execution_record.py`

## Core rule

A result may affect workflow state only through this chain:

`valid READY invocation + canonical stage/input/evidence/retrieval projection + executable stage role + exact input task commit + matching invocation_id + legal stage status + declared outputs + valid output task commit lineage + status-specific acceptance predicates + immutable evidence bindings when required + valid route key when routed -> execution record -> transition decision`

A prose answer, chat statement, reviewer conclusion, cache hit, retrieval-observer permission or unbound JSON object does not advance a Terminus stage by itself.

## Bootstrap identity

Durable lifecycle recording starts at `RULE_RESOLUTION`, so the controller reserves a safe stable `task_id` **before** that stage and binds the first invocation to an exact existing Git `task_commit`. For a new task that has not yet materialized task files, this commit is the repository/bootstrap snapshot from which creation begins. It is not evidence that task artifacts already exist.

A taskless invocation may still be compiled for an ephemeral preview, but it cannot be persisted into the task execution ledger. Do not invent a later task ID and retroactively rewrite earlier execution history.

## Explicit status semantics

`.terminus/agents/execution_outcomes.json` classifies every legal status of every registered stage into exactly one disposition:

- `ADVANCE` — the status may follow the declared `success_transition` only after required outputs, task lineage, acceptance predicates and required evidence bindings validate;
- `ROUTE` — return control through one declared `failure_routes` key;
- `RETRY` — repeat the same stage because the advancing condition is not yet satisfied;
- `BLOCK` — stop until the controller resolves the blocking condition.

No legal stage status may remain unclassified or belong to more than one disposition.

Examples:

- `FORMAT_GATE: FORMAT_PASS -> ADVANCE`;
- `FORMAT_GATE: FIXED -> RETRY`;
- `DETERMINISTIC_VALIDATION: PASS -> ADVANCE` only when Oracle=1, NOP=0 and F2P/P2P matrices are present;
- `QUALITY_INTERLOCK: QUALITY_INTERLOCK_PASS -> ADVANCE` only when the embedded current Q4/Q6 results satisfy the declared PASS/confidence/evidence predicates **and** are bound to immutable result references;
- `HARBOR_LLMAJ: PASS -> ADVANCE` only when the current external run identity and hashed run evidence agree;
- `OFFICIAL_MODEL_TRIALS: COMPLETE -> ADVANCE` only after the external batch identity and all ten distinct per-trial run identities are present;
- `QUALITY_INTERLOCK: REVISE -> ROUTE` through an allowed route such as `Q4_REVISE` or `Q6_REVISE`.

## Result envelope

Every executor result contains:

- `schema_version`;
- the exact `invocation_id`;
- `output_task_commit` — the task snapshot after this execution;
- one legal stage `status`;
- `outputs`, limited to declared stage fields;
- `evidence_refs`;
- `route_key` only for routed outcomes when required;
- `blocking_reason` for `BLOCK`.

The result contains no chain-of-thought, scratchpad or private-reasoning field.

### Do

- report the exact committed task snapshot actually produced or inspected;
- commit authorized producer/fixer changes before returning a result that relies on them;
- inspect the invocation's declared acceptance predicates before choosing an advancing status;
- preserve immutable evidence references for every acceptance-relevant external/reviewer fact;
- preserve reviewer IDs, external run IDs, trial run IDs and package identities needed to bind output values to evidence;
- return a non-advancing status when a required predicate or evidence binding is not satisfied;
- use the canonical execution recorder for external-gate results as well as ordinary stages.

### Do not

- report the invocation commit as `output_task_commit` after changing task artifacts;
- point `output_task_commit` at an uncommitted working tree, unrelated branch or non-descendant commit;
- let a controller, reviewer, simulator or external gate mutate the task snapshot while retaining that role authority;
- label a stage `PASS` merely because all required output *keys* are present;
- return an acceptance-sensitive PASS/COMPLETE with empty or unhashed evidence references;
- widen the invocation's evidence classes, insert undeclared inputs, relabel Oracle/verifier material as solver-visible content, or replace retrieved content and recompute `invocation_id`;
- weaken or fabricate embedded reviewer/run evidence to satisfy an aggregate predicate;
- rely on a CLI-specific validation path: the canonical recorder itself owns external-result and evidence checks.

## Invocation binding

The recorder recomputes the invocation identity and rejects a result when the invocation is not `READY`, the invocation ID does not match, the role is not the stage's canonical executable owner, or any canonical projection has been altered.

Durable revalidation includes:

- exact required/optional input names from the stage contract;
- canonical stage owner, role class and lifecycle;
- output contract and status vocabulary;
- acceptance-predicate projection;
- failure/success routing and staleness declarations;
- canonical authorized/excluded evidence classes;
- retrieval mode, mandatory exact reads and evidence requirements;
- retrieved source-kind/evidence-class compatibility;
- solver-visible-only restrictions;
- task/source-path classification so Oracle/test paths cannot be relabeled as public task code;
- retrieved content hash integrity for durable, non-truncated indexed context.

A durable record rejects truncated retrieved context because the clipped content cannot be revalidated against the source chunk's full content identity using the bounded packet alone. Use a new bounded invocation that contains complete authorized chunks instead.

Durable recording additionally requires `authority.task_id` and `authority.task_commit`. The invocation `task_commit` is always the **input task snapshot**. The result cannot replace task/control/packet authority fields; it supplies only the separately validated `output_task_commit`.

Retrieval audience remains separate. A controller may inspect a producer/reviewer stage without becoming that stage's executor.

## Task commit lineage

Every execution record persists:

```text
TASK_LINEAGE:
  INPUT_TASK_COMMIT:  <invocation authority.task_commit>
  OUTPUT_TASK_COMMIT: <result output_task_commit>
  TASK_CHANGED:       true | false
```

Rules:

1. both commits must exist in repository history;
2. `OUTPUT_TASK_COMMIT` must equal or descend from `INPUT_TASK_COMMIT`;
3. only `PRODUCER` and `FIXER` role classes may return a different output commit;
4. `CONTROLLER`, `REVIEWER`, `ADJUDICATOR`, `SIMULATOR` and external gate classes must preserve the exact input commit;
5. the next recorded stage must consume the previous current stage's output commit;
6. an unrecorded commit between stages is not silently absorbed by workflow state.

This allows a real lifecycle such as `A -> producer -> B -> reviewer/controller -> B -> fixer -> C` without making the earlier valid record stale merely because the task is now at C.

## Output validation

All output keys must be declared by the stage contract. Unknown keys fail closed. `full_output_statuses` declares statuses that require every stage-required output field; every advancing status is a full-output status.

The recorder never fills missing outputs from retrieval, chat memory, previous reviews or another record.

## Acceptance predicates

Field presence is not sufficient for acceptance. `.terminus/agents/stage_acceptance_predicates.json` defines fail-closed, status-specific value predicates for gates where an aggregate/status could otherwise self-assert success.

The predicate engine supports auditable structural/value operations only: equality, membership, empty/non-empty, exact collection length, numeric comparisons (`lt`, `lte`, `gt`, `gte`), collection-wide numeric lower bounds (`all_gte`) and equality to another declared output path (`eq_path`). It does **not** perform semantic reviewing. It verifies that the aggregate stage faithfully represents already-owned evidence.

Examples include:

- no unresolved policy conflicts for `RULES_RESOLVED`;
- Q1/Q2/Q3 success values for `SPEC_ALIGNMENT: ALIGNED`;
- runtime-authenticity status actually equal to PASS;
- Oracle/NOP/F2P/P2P facts for deterministic validation;
- Q4/Q6 PASS + adequate confidence + sufficient evidence for the quality interlock;
- all Pre-LLMaJ A–F aggregate stages marked PASS;
- exactly five GPT and five Claude official trials before `COMPLETE`;
- combined official success below 100%, every test solvable by at least one of ten trials, and empirical/declared difficulty agreement before Difficulty Assessment PASS;
- current successful Final Compliance/Human Quality evidence before `FINAL_REVIEW: PASS`;
- non-empty mandatory gate evidence before `SUBMISSION_READY`.

An `ADVANCE` result that fails a declared predicate is rejected before a durable execution record is created. A later state reconstruction rechecks the same predicates so a hand-forged historical record cannot bypass them.

## Evidence binding

Evidence references are not decorative metadata. Acceptance-sensitive advancing stages require immutable `content_hash`-bound references in addition to valid output values.

The canonical recorder currently enforces, at minimum:

- `QUALITY_INTERLOCK` — current Q4 and Q6 `review_id` values must each bind to hashed `RESULT` evidence;
- `PRE_LLMAJ` — the aggregate must retain the independent specialist/panel result set;
- `MODEL_DIAGNOSTIC_AGGREGATE` — both frozen Q8 perspective results must be referenced;
- `HARBOR_LLMAJ` — Harbor run identity must bind to hashed run/external evidence;
- `OFFICIAL_MODEL_TRIALS` — all ten distinct official trial `run_id` values must bind to immutable run evidence;
- `TRIAL_ANALYSIS` — all ten official trajectories remain evidence-bound;
- `DIFFICULTY_ASSESSMENT` — the ten official runs plus the Trajectory Analyst record are bound;
- `FINAL_REVIEW` — Compliance and Human Quality review IDs plus package evidence are bound;
- `SUBMISSION_READY` — validated gate result evidence and final package evidence are retained.

An evidence reference never becomes authoritative merely because it is named. Packet provenance, role-contract identity, task/control commit freshness, CI/external run identity and evidence-specific validators remain controlling.

## Route validation

For `ROUTE` statuses the route key must be allowed by the outcome contract and exist in the stage's `failure_routes`. A default route is legal only when explicitly declared. The record preserves the registered route instruction; it does not parse free-form prose into a new destination.

## Transition semantics

- `ADVANCE` -> declared success transition;
- `RETRY` -> same stage;
- `ROUTE` -> registered route key/instruction;
- `BLOCK` -> no target and a mandatory blocking reason.

Advance targets are `STAGE`, `STATE` or `END`. An `ADVANCE` to a non-executable state such as `FROZEN_CANDIDATE` sets `requires_state_validation=true`; the record alone is not proof that state-entry requirements are satisfied.

## FROZEN_CANDIDATE boundary

`DETERMINISTIC_VALIDATION: PASS` may transition toward `FROZEN_CANDIDATE`, but the controller still validates the state contract, including current format, complexity, runtime authenticity, Oracle/NOP/F2P/P2P and policy-conflict evidence. Only then may the controller proceed to `QUALITY_INTERLOCK`.

## Deterministic record identity

`record_id` is content-derived from invocation ID, stage/role authority, task lineage, status, outputs, evidence references, route/block fields and transition. It contains no timestamps or hidden reasoning. Equivalent validated results produce the same ID; any lineage/evidence/status/output change changes the ID.

## Persistence

The canonical durable location is:

`.terminus/executions/<task>/<invocation_id>.result.json`

Every durable task execution belongs to the task-scoped ledger. There is no hidden taskless bootstrap history: reserve the task identity first. Historical records are immutable; when evidence or contracts go stale, create a new invocation/result rather than rewriting provenance.

The append-only ledger and derived state rules are defined in `.terminus/agents/WORKFLOW_STATE.md`.

## Normal ChatGPT portability

Normal ChatGPT can apply the same contract through connected GitHub tooling when local Python is unavailable. The local implementation is the canonical validator/transition compiler and CI backstop; it does not make the workflow dependent on a particular agent runtime.
