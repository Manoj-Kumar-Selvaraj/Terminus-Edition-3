# Terminus Stage Invocation Contract

Stage-invocation policy version: `1.0`

This policy defines the executable handoff envelope used to invoke one registered Terminus stage/role pair. It compiles the existing lifecycle, evidence-visibility and retrieval contracts into a bounded machine-readable packet. It does not create a new lifecycle stage and does not change role authority.

Canonical implementation:

- `.terminus/execution/authority.py`
- `.terminus/execution/invocation.py`
- `.terminus/execution/cli.py`
- `.terminus/agents/schemas/stage_invocation.schema.json`
- `.terminus/validate_stage_invocation.py`

## Core rule

A stage invocation is a projection of already-authoritative contracts:

`stage contract + canonical executable owner role + exact task/control-plane identity + narrower packet/role restrictions + declared stage inputs + optional authorized retrieval context -> bounded invocation packet`

The packet is execution data, not semantic authority. It must never contain hidden chain-of-thought, private scratchpad reasoning, or an inferred PASS/acceptance decision.

## Input projection

The builder reads `input_contract.required_fields` and `input_contract.optional_fields` from `.terminus/agents/stage_contracts.json`.

- only declared required/optional fields may be projected to `inputs`;
- undeclared supplied fields are omitted entirely; only `ignored_input_count` is retained so even a rejected private field name is not leaked to the invoked role;
- missing required fields are listed in `missing_required_inputs`;
- a packet with missing required fields has `readiness=BLOCKED_MISSING_INPUTS` and is not executable;
- the builder must not fabricate a missing value from retrieval similarity, chat memory, or an unrelated durable artifact.

Input values may be scalar, structured JSON, or explicit artifact references. Durable evidence boundaries still control whether a value may be supplied to the selected role.

## Authority envelope

Every invocation records:

- `stage_id`;
- canonical executable owner `role_id`;
- stage owner and role class;
- `control_plane_commit`;
- task ID/task commit when task-scoped execution is identified;
- packet, role-contract, review-scope, CI-run and policy-version bindings when applicable;
- the resolved authorized and excluded evidence classes;
- the stage retrieval mode.

A task ID without an exact task commit, or a task commit without a task ID, is invalid. A control-plane commit is always required for a reproducible invocation.

The local canonical builder verifies that task/control commits exist in repository history. It also refuses to label the currently loaded stage/visibility/retrieval/invocation contracts as a different `control_plane_commit`: the machine contract files at that commit must byte-match the loaded contracts. Known supplied policy-version bindings are cross-checked against the actual policy files at that same commit.

This keeps the packet honest when task and control-plane snapshots differ and prevents a caller from combining current in-memory contracts with a stale or invented control-plane SHA.

## Execution authority versus retrieval audience

Retrieval/routing visibility and aggregate-stage execution authority are intentionally different contracts.

`.terminus/retrieval/policy.py` may authorize controllers or semantic reviewers to inspect evidence for a stage so they can route work, build packets, assess freshness and perform their narrower decision right. That observation/review permission does **not** make them the executor of the aggregate stage contract.

`.terminus/execution/authority.py` resolves exactly one executable owner role for each registered aggregate stage. Examples:

- `WORK_PACKAGE_RESEARCH` is executable by A1, not by CI Orchestrator merely because CI can inspect it;
- `SYSTEM_ARCHITECTURE` resolves to the A2 System Architect phase role;
- `ENVIRONMENT_BUILD` resolves to the A2 Environment Builder phase role;
- controller-owned aggregate stages are executable by their actual controller owner;
- `QUALITY_INTERLOCK` is executed/aggregated by its controller owner; Q4 and Q6 remain independent packet-bound reviewers whose results become stage inputs/evidence rather than alternative emitters of the aggregate `QUALITY_INTERLOCK` status;
- `PRE_LLMAJ` is executed/aggregated by its controller owner; Stage-B specialists, Comprehensive Reviewer and routed Adjudicator use their own reviewer contracts and feed the aggregate stage rather than sharing its output schema.

This separation preserves the single-owner rule and keeps the execution ledger unambiguous: one aggregate stage has one owner-issued stage result. Semantic reviewer conclusions stay independent evidence with their own packet/result provenance.

The executable owner must also be inside the stage's retrieval audience. A canonical role cannot borrow another stage's execution authority, and controller/reviewer observation cannot be promoted into aggregate-stage execution authority.

## Mandatory exact reads

All stage `policy_files` and `prompt_files` are returned under `mandatory_exact_reads` and must be read exactly by the executor. Similarity retrieval never substitutes for them.

The canonical local builder also verifies every declared exact-read path exists at `control_plane_commit` before issuing the packet.

The packet records references and the control-plane commit; it does not inline whole policies by default. Normal ChatGPT may satisfy these reads through the GitHub connector. Local/Codex/Work execution may read them from the exact Git snapshot.

## Retrieval projection

Retrieval is optional. When an authorized local index and query are available, the builder may attach bounded `retrieved_context` produced by `.terminus/retrieval/engine.py`.

Retrieval state is one of:

- `INDEXED_CONTEXT` — authorized indexed evidence was queried;
- `DIRECT_READ_FALLBACK` — retrieval was requested but no usable local index exists;
- `NOT_REQUESTED` — no retrieval query was requested;
- `SKIPPED_BLOCKED_INPUTS` — the caller requested retrieval, but declared required stage inputs are missing, so the builder does not expose additional indexed evidence to a non-executable handoff.

The absence of a local index does not make an otherwise valid stage invocation impossible. The executor continues through direct exact reads of authorized evidence.

Retrieved context never expands stage/role/packet evidence authority and never satisfies a missing required stage input automatically. Retrieved-context schema is fail closed and permits only the provenance/content/ranking fields emitted by the canonical context builder.

## Output contract projection

Every invocation includes the selected aggregate stage's:

- legal `status_values`;
- required and optional output fields;
- persisted-artifact declarations;
- deterministic validators;
- semantic reviewers that provide required semantic evidence;
- required evidence description;
- failure routes;
- success transition;
- staleness triggers.

The stage owner must return one legal aggregate-stage status and the fields required for that status/execution. Semantic reviewers return through their role-specific packet/result contracts, not by pretending their verdict is the aggregate stage status. A later execution-record/state-transition layer validates the owner's returned result; the invocation builder itself does not certify completion.

## Deterministic identity

`invocation_id` is derived from the canonical packet content excluding the ID itself. The digest changes when authority bindings, projected inputs, output contract, exact-read set, exclusions, retrieval order/content or retrieved chunk provenance change.

Diagnostic retrieval score magnitudes are explicitly excluded from invocation identity. The retrieval cache is allowed to reconstruct diagnostic scores from rank order, so cached-versus-fresh score telemetry must not produce two invocation IDs for the same authorized ordered evidence set.

Timestamps are deliberately not part of the identity. Rebuilding the same bounded invocation from the same immutable state yields the same `invocation_id`.

## No hidden reasoning

The schema deliberately has no `chain_of_thought`, `reasoning`, `scratchpad`, or equivalent private-reasoning field. Agent reasoning stays runtime-local. Persisted/exchanged material is limited to task/control data, evidence references, concise findings/statuses and declared stage outputs.

## Failure behavior

Fail closed when:

- stage or role is unknown;
- role is not the canonical executable owner of the aggregate stage;
- controller/reviewer retrieval observation is incorrectly used as aggregate-stage execution authority;
- control-plane commit is missing, unavailable, or does not match the loaded machine contracts;
- a mandatory exact-read path does not exist at the bound control-plane commit;
- task ID/task commit binding is incomplete or its commit is unavailable;
- a known supplied policy-version binding is stale against the bound control-plane commit;
- a narrower evidence restriction references an unknown evidence class;
- retrieval context cannot pass the existing authorization/freshness policy.

Return a non-executable blocked packet, rather than raising, only for ordinary missing declared stage inputs. Authority/provenance errors are construction errors and must raise/fail.

## Portability

This contract remains executable from normal ChatGPT. A chat executor can consume the generated structure conceptually or reconstruct it through exact GitHub reads when local execution is unavailable. Independent reviewer chats continue to use their generated reviewer packets/role contracts; the owning controller then consumes their current results when executing the aggregate stage. The local builder is the canonical machine implementation, not a requirement that every ChatGPT surface run Python or SQLite.
