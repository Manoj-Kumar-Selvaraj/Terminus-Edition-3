# Terminus Execution Record and Transition Contract

Execution-record policy version: `1.0`

This policy defines how one completed stage invocation is converted into a durable, machine-readable execution record and a deterministic transition decision. It consumes the bounded invocation produced under `.terminus/agents/STAGE_INVOCATION.md`; it does not create new role authority, infer missing evidence, or certify semantic correctness beyond the declared stage/result contract.

Canonical implementation:

- `.terminus/agents/execution_outcomes.json`
- `.terminus/agents/schemas/execution_outcomes.schema.json`
- `.terminus/agents/schemas/stage_result.schema.json`
- `.terminus/agents/schemas/execution_record.schema.json`
- `.terminus/execution/authority.py`
- `.terminus/execution/record.py`
- `.terminus/execution/result_cli.py`
- `.terminus/validate_execution_record.py`

## Core rule

A result may affect workflow state only through this chain:

`valid READY invocation + executable stage role + matching invocation_id + legal stage status + declared output keys + status-specific required outputs + valid route key when routed -> execution record -> transition decision`

A prose answer, chat statement, reviewer conclusion, cache hit, retrieval-observer permission or unbound JSON object does not advance a Terminus stage by itself.

## Explicit status semantics

`.terminus/agents/execution_outcomes.json` classifies every legal status of every registered stage into exactly one disposition:

- `ADVANCE` — this status may follow the stage's declared `success_transition` after required outputs validate;
- `ROUTE` — this status returns control through one declared `failure_routes` key; it never guesses a destination from free-form prose;
- `RETRY` — this status repeats the same stage because the stage has not yet reached its advancing condition;
- `BLOCK` — this status stops execution until the controller resolves the blocking condition.

No legal stage status may remain unclassified. No status may appear in more than one disposition.

Examples:

- `FORMAT_GATE: FORMAT_PASS -> ADVANCE`;
- `FORMAT_GATE: FIXED -> RETRY`, because the gate must be rerun until it actually reports `FORMAT_PASS`;
- `MODEL_DIAGNOSTIC: SIMULATION_NOT_EXECUTED -> ADVANCE`, because Q8 is diagnostic and must not become fabricated official evidence;
- `DETERMINISTIC_VALIDATION: PASS -> ADVANCE` to the non-executable `FROZEN_CANDIDATE` state, which still requires its explicit state-entry validation before `QUALITY_INTERLOCK`;
- `QUALITY_INTERLOCK: REVISE -> ROUTE` with an allowed route key such as `Q4_REVISE` or `Q6_REVISE`.

## Result envelope

The executor returns a compact stage-result envelope containing:

- `schema_version`;
- the exact `invocation_id` it executed;
- one legal stage `status`;
- `outputs`, limited to fields declared by the invocation output contract;
- `evidence_refs`, as explicit artifact/run/packet/result/commit/file/external references;
- `route_key` only when the outcome contract requires or permits routing;
- `blocking_reason` when disposition is `BLOCK`.

The envelope has no chain-of-thought, scratchpad or private-reasoning field.

## Invocation binding

The recorder recomputes the supplied invocation identity using the same canonical identity rule as `StageInvocationBuilder`. A result is rejected when:

- the invocation is not `READY`;
- `invocation_id` does not match the invocation content;
- the result names a different invocation ID;
- the stage/role/output contract has been altered inside the invocation packet;
- the invocation role is not in the stage's executable-role set from `.terminus/execution/authority.py`;
- a controller/retrieval observer has been forged into a producer/reviewer executor;
- the loaded execution-outcome contract does not byte-match the invocation's bound `control_plane_commit`.

The record copies the invocation's stage, executable role and authority envelope. It never accepts replacement task/control-plane/packet identities from the result payload.

Retrieval audience remains separate: a controller may be allowed to inspect a stage's evidence for orchestration without being allowed to produce that stage's execution record. Record validation rechecks executable authority even if a forged invocation ID is internally self-consistent.

## Output validation

All returned output keys must be declared by the invocation as required or optional stage outputs. Unknown output keys fail closed rather than being silently persisted.

`full_output_statuses` in `execution_outcomes.json` declares which statuses require every stage `required_fields` entry. Advancing statuses are always full-output statuses. Routed/retry statuses may also require the full output contract when the stage can reasonably produce it; evidence-insufficiency and hard-block conditions may remain partial.

A missing required output for a full-output status rejects the result. The recorder never fills an output from retrieval, chat memory, previous reviews or a prior execution record.

## Route validation

For `ROUTE` statuses:

- the route key must be one of the outcome contract's `allowed_route_keys`;
- a `default_route_key` may be used only when the outcome contract explicitly declares one;
- the final route key must exist in the invocation's `failure_routes` map;
- the execution record carries the exact registered `route_instruction` string;
- the transition engine does not parse that prose into an invented stage ID.

If the route outcome permits several owners, the role/controller must provide the route key that matches the observed failure class.

## Transition semantics

The execution record emits one transition decision:

- `ADVANCE` -> target is the invocation's `success_transition`;
- `RETRY` -> target is the current stage;
- `ROUTE` -> target kind is `ROUTE`, with route key/instruction and no fabricated stage target;
- `BLOCK` -> no target; `blocking_reason` is mandatory.

Advance targets are classified as:

- `STAGE` when the target is another registered executable stage;
- `STATE` when the target is a registered non-executable state such as `FROZEN_CANDIDATE`;
- `END` for terminal submission completion.

An `ADVANCE` into a non-executable state sets `requires_state_validation=true`. The execution record is not proof that the state-entry requirements themselves have been satisfied.

## FROZEN_CANDIDATE boundary

`DETERMINISTIC_VALIDATION: PASS` may produce an execution-record transition toward `FROZEN_CANDIDATE`, but the controller must still validate the state contract in `.terminus/agents/stage_contract_completion.json`, including current format, complexity, runtime-authenticity, Oracle/NOP/F2P/P2P and policy-conflict evidence.

Only after that state-entry contract is current may the controller exit the state to `QUALITY_INTERLOCK`.

## Deterministic record identity

`record_id` is content-derived from the validated invocation ID, stage/role authority, status, outputs, evidence references, route/block fields and transition decision. It does not include timestamps or hidden reasoning.

Equivalent validated results against the same invocation produce the same record ID. A changed status, output, evidence reference, route or invocation produces a different ID.

## Evidence references

Execution records preserve references; they do not make a referenced artifact authoritative merely by naming it. Protocol, packet provenance, review freshness, CI run identity and evidence-specific validators remain responsible for deciding whether a reference is current and sufficient.

Semantic acceptance is never inferred from the mere existence or count of evidence references.

## Persistence

The canonical durable location for a task-scoped record is:

`.terminus/executions/<task>/<invocation_id>.result.json`

Controller-only/non-task bootstrap records may be stored under an explicitly selected control-plane execution path when durable persistence is useful. Persistence is optional for ephemeral local diagnostics but mandatory whenever a later stage/session relies on the result as durable evidence.

A persisted execution record is audit history, not mutable workflow memory. If its task/control-plane/evidence bindings go stale, create a new invocation/record rather than rewriting historical provenance.

The append-only task execution ledger and derived current-state rules are defined by `.terminus/agents/WORKFLOW_STATE.md`. The record is durable provenance; the materialized workflow snapshot is rebuildable derived state.

## Normal ChatGPT portability

Normal ChatGPT can still execute the workflow without running the Python recorder locally. The repository contract is authoritative: a chat/controller may construct the same result envelope and persist it through GitHub tooling when authorized. The local implementation is the canonical validator/transition compiler and CI backstop, not a requirement that every chat surface expose a Python runtime.
