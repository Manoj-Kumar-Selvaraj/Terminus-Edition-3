# Terminus Edition 3 Structured Stage Contracts

Stage-contract policy version: `1.0`

This file explains how execution-relevant sections of `.terminus/AGENT_SYSTEM.md` bind to concrete agents, policy/prompt files, input/output contracts, evidence, validators/reviewers, failure routes, transitions and staleness rules.

The canonical machine-readable lifecycle registry is `.terminus/agents/stage_contracts.json`. Its structural schema is `.terminus/agents/schemas/stage_contracts.schema.json`.

The lifecycle registry is complemented by:
- `.terminus/agents/evidence_visibility.json` and `.terminus/agents/EVIDENCE_VISIBILITY.md` for v1.1 evidence/retrieval authorization;
- `.terminus/agents/stage_contract_completion.json` and `.terminus/agents/STAGE_CONTRACT_COMPLETION.md` for v1.2 phase ordering and explicit lifecycle-state semantics.

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

## Staleness principle

`stale_on` fields are stage-level dependency declarations. They supplement, not weaken, `PROTOCOL.md` and role-specific freshness rules.

Where Protocol defines a stricter exact-commit or scope-hash rule, that stricter rule controls. Stage contracts must never be used to preserve evidence that Protocol declares stale.

## Layer resolution

Controllers resolve the structured contract in this order:

1. `stage_contracts.json` — lifecycle owner, input/output, routing and stage-local staleness;
2. `stage_contract_completion.json` — phase ordering and explicit non-executable state boundaries;
3. `evidence_visibility.json` — required/optional/excluded evidence classes and retrieval mode;
4. role/packet-specific rules — narrower evidence and provenance restrictions.

A lower layer may narrow an earlier layer; it may never widen a higher-precedence policy or evidence boundary. Future RAG/caching must consume the same resolved contract and cannot bypass phase, freeze, visibility or freshness rules.