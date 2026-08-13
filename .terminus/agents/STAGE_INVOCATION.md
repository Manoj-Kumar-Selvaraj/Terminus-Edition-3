# Terminus Stage Invocation Contract

Stage-invocation policy version: `1.0`

This policy defines the executable handoff envelope used to invoke one registered Terminus stage/role pair. It compiles the existing lifecycle, evidence-visibility and retrieval contracts into a bounded machine-readable packet. It does not create a new lifecycle stage and does not change role authority.

Canonical implementation:

- `.terminus/execution/invocation.py`
- `.terminus/execution/cli.py`
- `.terminus/agents/schemas/stage_invocation.schema.json`
- `.terminus/validate_stage_invocation.py`

## Core rule

A stage invocation is a projection of already-authoritative contracts:

`stage contract + canonical stage-authorized role + exact task/control-plane identity + narrower packet/role restrictions + declared stage inputs + optional authorized retrieval context -> bounded invocation packet`

The packet is execution data, not semantic authority. It must never contain hidden chain-of-thought, private scratchpad reasoning, or an inferred PASS/acceptance decision.

## Input projection

The builder reads `input_contract.required_fields` and `input_contract.optional_fields` from `.terminus/agents/stage_contracts.json`.

- only declared required/optional fields may be projected to `inputs`;
- undeclared supplied fields are omitted and listed in `ignored_input_fields`;
- missing required fields are listed in `missing_required_inputs`;
- a packet with missing required fields has `readiness=BLOCKED_MISSING_INPUTS` and is not executable;
- the builder must not fabricate a missing value from retrieval similarity, chat memory, or an unrelated durable artifact.

Input values may be scalar, structured JSON, or explicit artifact references. Durable evidence boundaries still control whether a value may be supplied to the selected role.

## Authority envelope

Every invocation records:

- `stage_id`;
- canonical `role_id`;
- stage owner and role class;
- `control_plane_commit`;
- task ID/task commit when task-scoped execution is identified;
- packet, role-contract, review-scope, CI-run and policy-version bindings when applicable;
- the resolved authorized and excluded evidence classes;
- the stage retrieval mode.

A task ID without an exact task commit, or a task commit without a task ID, is invalid. A control-plane commit is always required for a reproducible invocation.

The role must be authorized for the stage according to `.terminus/retrieval/policy.py`; a canonical role cannot borrow another stage's authority.

## Mandatory exact reads

All stage `policy_files` and `prompt_files` are returned under `mandatory_exact_reads` and must be read exactly by the executor. Similarity retrieval never substitutes for them.

The packet records references and the control-plane commit; it does not inline whole policies by default. Normal ChatGPT may satisfy these reads through the GitHub connector. Local/Codex/Work execution may read them from the exact Git snapshot.

## Retrieval projection

Retrieval is optional. When an authorized local index and query are available, the builder may attach bounded `retrieved_context` produced by `.terminus/retrieval/engine.py`.

Retrieval state is one of:

- `INDEXED_CONTEXT` — authorized indexed evidence was queried;
- `DIRECT_READ_FALLBACK` — retrieval was requested but no usable local index exists;
- `NOT_REQUESTED` — no retrieval query was requested.

The absence of a local index does not make an otherwise valid stage invocation impossible. The executor continues through direct exact reads of authorized evidence.

Retrieved context never expands stage/role/packet evidence authority and never satisfies a missing required stage input automatically.

## Output contract projection

Every invocation includes the selected stage's:

- legal `status_values`;
- required and optional output fields;
- persisted-artifact declarations;
- deterministic validators;
- semantic reviewers;
- required evidence description;
- failure routes;
- success transition;
- staleness triggers.

The executor must return one legal stage status and the fields required for that status/execution. A later execution-record/state-transition layer validates the returned result; the invocation builder itself does not certify completion.

## Deterministic identity

`invocation_id` is derived from the canonical packet content excluding the ID itself. The digest therefore changes when authority bindings, projected inputs, output contract, exact-read set, exclusions or retrieved chunk provenance change.

Timestamps are deliberately not part of the identity. Rebuilding the same bounded invocation from the same immutable state yields the same `invocation_id`.

## No hidden reasoning

The schema deliberately has no `chain_of_thought`, `reasoning`, `scratchpad`, or equivalent private-reasoning field. Agent reasoning stays runtime-local. Persisted/exchanged material is limited to task/control data, evidence references, concise findings/statuses and declared stage outputs.

## Failure behavior

Fail closed when:

- stage or role is unknown;
- role is not authorized for the stage;
- control-plane commit is missing/invalid;
- task ID/task commit binding is incomplete;
- a narrower evidence restriction references an unknown evidence class;
- retrieval context cannot pass the existing authorization/freshness policy.

Return a non-executable blocked packet, rather than raising, only for ordinary missing declared stage inputs. Authority/provenance errors are construction errors and must raise/fail.

## Portability

This contract remains executable from normal ChatGPT. A chat executor can consume the generated structure conceptually or reconstruct it through exact GitHub reads when local execution is unavailable. The local builder is the canonical machine implementation, not a requirement that every ChatGPT surface run Python or SQLite.
