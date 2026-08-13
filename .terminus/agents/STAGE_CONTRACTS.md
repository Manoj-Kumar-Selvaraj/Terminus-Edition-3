# Terminus Edition 3 Structured Stage Contracts

Stage-contract policy version: `1.0`

This file explains how execution-relevant sections of `.terminus/AGENT_SYSTEM.md` bind to concrete agents, policy/prompt files, input/output contracts, evidence, validators/reviewers, failure routes, transitions and staleness rules.

The canonical machine-readable lifecycle registry is `.terminus/agents/stage_contracts.json`. Its structural schema is `.terminus/agents/schemas/stage_contracts.schema.json`.

The lifecycle registry is complemented by:
- `.terminus/agents/evidence_visibility.json` and `.terminus/agents/EVIDENCE_VISIBILITY.md` for v1.1 evidence/retrieval authorization;
- `.terminus/agents/stage_contract_completion.json` and `.terminus/agents/STAGE_CONTRACT_COMPLETION.md` for v1.2 phase ordering and explicit lifecycle-state semantics;
- `.terminus/agents/retrieval_metadata.json` and `.terminus/agents/RETRIEVAL_METADATA.md` for the canonical provenance/chunk/index envelope;
- `.terminus/agents/DYNAMIC_EVIDENCE_INGESTION.md` for explicit provenance-aware persistence of review, session, CI, model-trial, final-package and public-reference evidence;
- `.terminus/agents/RETRIEVAL_ENGINE.md` and `.terminus/retrieval/` for the optional local exact/BM25/vector/hybrid retrieval adapter and its caches;
- `.terminus/agents/STAGE_INVOCATION.md` and `.terminus/execution/invocation.py` for deterministic bounded stage/role handoffs;
- `.terminus/agents/EXECUTION_RECORD.md`, `.terminus/agents/execution_outcomes.json` and `.terminus/execution/record.py` for result binding and explicit ADVANCE/ROUTE/RETRY/BLOCK transitions.

`AGENT_SYSTEM.md` remains the system-wide policy/ownership source. These files specialize execution structure; they do not override higher-precedence Edition 3 rules, Protocol evidence boundaries, packet exclusions, or role authority.

## Why this exists

A control-plane policy is incomplete when it says *what should happen* but leaves an agent to infer:

- which role owns the step;
- which detailed policy and runnable prompt apply;
- what the role may consume;
- what exact output shape the next stage expects;
- what evidence makes the output usable;
- which machine validators exist versus which checks require semantic judgment;
- where failures route;
- what state follows success;
- what changes make prior evidence stale.

The stage registry makes these interfaces explicit so a controller can route work without reconstructing the workflow from scattered prose.

## Canonical stage fields

Every registered stage defines:

- `id` — stable lifecycle identifier;
- `lifecycle` — `creation | review | evaluation | submission`;
- `owner` — the single primary decision/execution owner for the stage;
- `role_class` — control-plane class (`CONTROLLER`, `PRODUCER`, `FIXER`, `REVIEWER`, `ADJUDICATOR`, `SIMULATOR`, or `EXTERNAL_GATE`);
- `policy_files` — authoritative/narrow policy files the stage must follow;
- `prompt_files` — executable role prompt/contract files used when the owner is invoked;
- `input_contract.required_fields` — fields/artifacts the stage cannot run correctly without;
- `input_contract.optional_fields` — useful but non-mandatory context;
- `output_contract.status_values` — stage-valid status vocabulary;
- `output_contract.required_fields` — fields the next controller/stage may rely on;
- `output_contract.optional_fields` — role-specific additional evidence;
- `output_contract.persisted_artifacts` — durable artifacts when the stage produces any;
- `evidence_required` — what must support the stage output before advancement;
- `deterministic_validators` — actual machine checks that exist or mechanically enforce part of the stage contract;
- `semantic_reviewers` — roles that judge non-mechanical quality/acceptance aspects;
- `failure_routes` — explicit ownership for known failure classes;
- `success_transition` — next lifecycle stage after valid completion;
- `stale_on` — material changes that invalidate the stage's prior output/evidence.

## Validator honesty rule

Do not list a semantic expectation as a deterministic validator merely because it is desirable.

Examples:

- `validate_agent_system.py` can verify control-plane structure and required policy/schema markers.
- `validate_task_complexity.py` can enforce defined structural complexity conditions.
- `validate_review_freshness.py` can verify provenance/currentness rules.
- whether a Jira-style instruction is genuinely natural, fair and non-leaky remains a semantic reviewer judgment even if some mechanical instruction-shape checks are possible.

An empty `deterministic_validators` list is correct when no honest machine validator exists.

## Input/output contract rule

Input/output field contracts are canonical **interfaces**, not permission to expose hidden evidence to a role.

A stage still obeys the role's evidence boundary and generated packet. If a registry field names material that is excluded for a particular execution, the controller must not pass it merely because the generic stage supports it.

Persisted artifacts with stable cross-agent consumption should use a machine schema when useful. Ephemeral handoffs may remain structured text fields until they become durable interfaces. Do not create one JSON schema per stage solely for symmetry.

## Runtime prompt projection

The controller should project, for the selected stage:

1. the stage ID and owner;
2. the minimum applicable policy excerpts/references;
3. the role's allowed evidence;
4. the required input fields available for this execution;
5. exclusions/permissions;
6. the required output/status contract;
7. the completion condition and failure route.

Do not inject the entire stage registry or entire control plane when one bounded contract is sufficient.

When retrieval is available, the controller first resolves stage/role/packet authorization, exact-reads the stage-declared `policy_files`/`prompt_files`, then applies `.terminus/agents/RETRIEVAL_METADATA.md` and `.terminus/agents/RETRIEVAL_ENGINE.md` only to select additional authorized evidence. Retrieval is an optional projection adapter, not a new lifecycle stage and not an authority source. Metadata, ranking or cache hits may narrow/select context; they never expand the evidence pool authorized by the stage/role/packet contract.

When dynamic evidence is useful for local persistence/retrieval, the controller additionally applies `.terminus/agents/DYNAMIC_EVIDENCE_INGESTION.md` before persistence. Dynamic ingestion is optional and explicit: review/session/CI/model/final/public material is never accepted merely because it exists, and every persisted projection must retain truthful source provenance plus the selected stage/consumer-role ceiling.

If the local retrieval index is absent or the execution surface cannot run it, continue through direct exact repository/GitHub reads of the same authorized evidence. Missing RAG infrastructure by itself is not `INSUFFICIENT_EVIDENCE` when the required evidence remains directly accessible.

## Retrieval adapter contract

For a registered stage, the controller may use `.terminus/retrieval/cli.py context` or the equivalent library API after stage resolution. The adapter returns:

- `mandatory_exact_reads` — stage policy/prompt files that must still be read exactly;
- `authorized_evidence_classes` — the resolved evidence-class ceiling after stage/role restrictions;
- bounded retrieved chunks with source path/kind, evidence class, structural locator and score.

The controller must preserve narrower packet/role exclusions when constructing the `InvocationContext`. Packet-bound reviewers remain packet-bound even when the physical SQLite index contains broader material.

The local index is built from immutable Git blobs and is commit-bound. Dynamic review/session/CI/model/final/public evidence is not auto-classified by the repository scanner because packet hashes, run IDs and role/review-scope bindings must come from explicit provenance-aware ingestion or direct reads. The implemented `DynamicEvidenceIngestor` performs that optional persistence only after pre-persistence authorization.

## Stage invocation and execution recording

Before a registered role is actually invoked, the controller applies `.terminus/agents/STAGE_INVOCATION.md` and compiles one bounded invocation packet. The packet binds the exact stage/role, task/control-plane identity, declared inputs, exact reads, evidence ceiling, optional retrieved context, legal output contract and routing/staleness contract. A packet with missing required stage inputs is non-executable.

After the role returns, the controller applies `.terminus/agents/EXECUTION_RECORD.md`. A result can affect workflow state only when it:

1. names the exact `invocation_id` it executed;
2. returns one legal status for that stage;
3. returns only declared output fields;
4. satisfies the status-specific full-output requirement from `.terminus/agents/execution_outcomes.json`;
5. supplies an allowed failure-route key when the status is routed and no unique default exists;
6. binds material evidence through explicit references rather than prose claims.

The canonical result compiler emits one immutable execution record and one disposition: `ADVANCE | ROUTE | RETRY | BLOCK`. A chat statement such as “PASS” or “done” does not advance a stage by itself.

`ADVANCE` follows the stage's exact `success_transition`. `RETRY` repeats the current stage. `ROUTE` carries the exact declared failure-route instruction without guessing a stage ID from prose. `BLOCK` has no target and requires an explicit blocking reason.

When an advancing target is a non-executable state such as `FROZEN_CANDIDATE`, the record sets `requires_state_validation=true`; the controller must still satisfy the state's entry contract before exiting it to the next executable stage.

## Creation stage index

The canonical creation path is:

`RULE_RESOLUTION -> WORK_PACKAGE_RESEARCH -> SYSTEM_ARCHITECTURE -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD -> REFERENCE_SOLUTION -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT -> DOCUMENTATION_DRAFT -> FORMAT_GATE -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK`

`SYSTEM_ARCHITECTURE`, `DEFECT_TOPOLOGY`, and `ENVIRONMENT_BUILD` have additional phase constraints in `.terminus/agents/stage_contract_completion.json`:
- `SYSTEM_ARCHITECTURE` is the first A2 invocation and is **design-only**;
- `DEFECT_TOPOLOGY` designs against that approved clean architecture;
- `ENVIRONMENT_BUILD` is the second A2 invocation and materializes the starter from both approved architecture and topology.

`FROZEN_CANDIDATE` is a controller state with an explicit state contract in the completion overlay. It is reached only after successful deterministic validation and exits only to `QUALITY_INTERLOCK` when its exact evidence remains current.

## Review/evaluation/submission index

`QUALITY_INTERLOCK -> PRE_LLMAJ -> MODEL_DIAGNOSTIC -> OFFICIAL_MODEL_TRIALS -> TRIAL_ANALYSIS -> FINAL_REVIEW -> SUBMISSION_READY`

Harbor LLMaJ remains a required external gate in the broader review order. The Orchestrator must preserve the ordering defined by `AGENT_SYSTEM.md`/`PRE_LLMAJ.md`; the registry does not reinterpret external platform semantics.

## Section-to-stage bindings

Execution-relevant `AGENT_SYSTEM.md` sections should cite one or more stage IDs rather than duplicating full contracts.

| AGENT_SYSTEM area | Primary stage contract(s) |
| --- | --- |
| creation bootstrap / rule resolution | `RULE_RESOLUTION` |
| large-system work-package selection | `WORK_PACKAGE_RESEARCH` |
| production architecture / starter | `SYSTEM_ARCHITECTURE`, `DEFECT_TOPOLOGY`, `ENVIRONMENT_BUILD` |
| reference solution | `REFERENCE_SOLUTION` |
| verifier authoring | `VERIFIER_BUILD` |
| human writing calibration | `HUMAN_WRITING_RESEARCH` |
| human engineering instruction policy | `INSTRUCTION_DRAFT`, `SPEC_ALIGNMENT` |
| task documentation | `DOCUMENTATION_DRAFT` |
| format compliance | `FORMAT_GATE` |
| assembly / deterministic authoring evidence | `ASSEMBLY`, `DETERMINISTIC_VALIDATION`, `FROZEN_CANDIDATE` |
| large-system complexity/authenticity | `COMPLEXITY_GATE`, `RUNTIME_AUTHENTICITY` |
| Q4/Q6 quality interlock | `QUALITY_INTERLOCK` |
| ordinary specialist/comprehensive review | `PRE_LLMAJ` |
| pre-model diagnostic simulation | `MODEL_DIAGNOSTIC` |
| official difficulty/solvability | `OFFICIAL_MODEL_TRIALS`, `TRIAL_ANALYSIS` |
| final compliance/human/package review | `FINAL_REVIEW` |
| submission readiness | `SUBMISSION_READY` |

## Instruction specialization

Detailed instruction authoring/review semantics are owned by `.terminus/agents/INSTRUCTION_POLICY.md` and stage `INSTRUCTION_DRAFT`.

The registry therefore gives the controller the structured interface, while `INSTRUCTION_POLICY.md` gives the human/semantic content policy. Q1/Q3/Q4 and Instruction Reviewer consume both according to their bounded decision rights.

## Failure routing principle

Stage failure routes are routing hints under the system's single-owner rule, not permission for the controller to perform the repair itself.

When evidence indicates a different owner than the registry's common failure route, the controller should route to the smallest correct owner under `AGENT_SYSTEM.md`, `PROTOCOL.md` and the role registries. A material policy conflict overrides ordinary routing and blocks the affected gate.

The execution-record layer never parses a human-readable route instruction into a guessed stage. It validates a route key against the stage contract, preserves the registered instruction verbatim, and returns control to the controller for the next bounded invocation.

## Staleness principle

`stale_on` fields are stage-level dependency declarations. They supplement, not weaken, `PROTOCOL.md` and role-specific freshness rules.

Where Protocol defines a stricter exact-commit or scope-hash rule, that stricter rule controls. Stage contracts must never be used to preserve evidence that Protocol declares stale.

Retrieval indexes, dynamic projections and caches are subject to the same principle. `.terminus/agents/retrieval_metadata.json` declares content/commit/policy/packet freshness scopes for indexed units; a retrieval cache, index hit or ingested dynamic projection is unusable when any declared binding is stale. Parse/chunk reuse is keyed by immutable source version + chunking strategy/version, embedding reuse is keyed by content/provider identity, and retrieval-result reuse is authority/query/index-bound and re-authorized before use. Semantic verdicts are never cached by this layer.

Invocation packets and execution records are immutable provenance objects. A stale dependency invalidates their use for advancement; it does not authorize rewriting their historical task/control-plane/evidence identity. Create a new invocation and result record when rerunning stale work.

## Layer resolution

Controllers resolve the structured contract in this order:

1. `stage_contracts.json` — lifecycle owner, input/output, routing and stage-local staleness;
2. `stage_contract_completion.json` — phase ordering and explicit non-executable state boundaries;
3. `evidence_visibility.json` — required/optional/excluded evidence classes and retrieval mode;
4. role/packet-specific rules — narrower evidence and provenance restrictions;
5. `retrieval_metadata.json` — immutable source identity, chunking, applicability and freshness metadata for the already-authorized candidate pool;
6. `DYNAMIC_EVIDENCE_INGESTION.md` / `DynamicEvidenceIngestor` — optional explicit persistence of authorized dynamic evidence with embedded/source provenance verification;
7. `RETRIEVAL_ENGINE.md` / `.terminus/retrieval/` — optional exact/BM25/vector/hybrid ranking, context assembly and cache reuse over that authorized pool;
8. `STAGE_INVOCATION.md` / `StageInvocationBuilder` — bounded executable handoff compiled from the resolved authority and declared stage interface;
9. `EXECUTION_RECORD.md` / `execution_outcomes.json` / `ExecutionRecordBuilder` — validated result binding and deterministic ADVANCE/ROUTE/RETRY/BLOCK transition.

A lower layer may narrow an earlier layer; it may never widen a higher-precedence policy or evidence boundary. Dynamic ingestion, retrieval, invocation compilation, result recording and caching consume the same resolved contract and cannot bypass phase, freeze, visibility or freshness rules.
