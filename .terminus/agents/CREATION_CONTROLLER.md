# Terminus Edition 3 Creation Controller

Policy version: `1.0`

This controller is mandatory for new/rebuilt tasks. Current Edition 3 rules override local policy on conflict. Every creation run also applies `.terminus/agents/PRODUCTION_AUTHENTICITY.md` and the additive quality interlock in `.terminus/agents/QUALITY_AGENT_REGISTRY.md`.

## States

`CREATION_REQUEST -> RULE_RESOLUTION -> IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT -> DOCUMENTATION_DRAFT -> FORMAT_GATE -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK`

`BLOCKED` may overlay any state.

The canonical structured interfaces for execution stages are in `.terminus/agents/stage_contracts.json`, with semantics in `.terminus/agents/STAGE_CONTRACTS.md`. Those contracts specialize routing/interface structure and never override higher-precedence Edition 3 or Protocol rules.

## Structured stage-contract routing

Before invoking a registered creation stage, the controller must:

1. resolve the stage entry from `.terminus/agents/stage_contracts.json`;
2. verify the declared primary owner and role class match the intended invocation;
3. load the stage's applicable `policy_files` and `prompt_files` under normal precedence;
4. verify every `input_contract.required_fields` item is available, current and allowed by the role's evidence boundary;
5. pass only the minimum relevant allowed input fields rather than the entire control plane;
6. require the role to return one declared `output_contract.status_values` value plus every required output field;
7. preserve declared `persisted_artifacts` and evidence references when the stage produces durable evidence;
8. run only the listed deterministic validators that actually apply and exist; semantic reviewers remain semantic owners and are not replaced by validator output;
9. route failures using the declared common `failure_routes`, unless current evidence/higher-precedence policy requires a smaller or stricter owner;
10. advance only to the declared `success_transition` after evidence and predecessor requirements are satisfied;
11. invalidate prior stage evidence when a material `stale_on` dependency changes, subject to stricter Protocol exact-commit/scope-hash rules.

A stage registry field is not permission to disclose excluded evidence. The generated role packet/evidence boundary still controls what an agent may see.

For `INSTRUCTION_DRAFT`, `.terminus/agents/INSTRUCTION_POLICY.md` is mandatory detailed policy in addition to the stage input/output contract.

## Creation bootstrap / rule resolution

No producer starts scenario design until the controller has resolved one creation-rule context for the run.

At `RULE_RESOLUTION`, the controller must:
1. resolve the exact control-plane commit used for creation;
2. read the current repository-wide task rules in `TERMINUS_3_AI_INSTRUCTIONS.md`;
3. read `.terminus/reviewers/REVIEWER_CHECKLIST.md`, `.terminus/agents/CREATION_PIPELINE.md`, `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/agents/QUALITY_AGENT_REGISTRY.md`, `.terminus/agents/STAGE_CONTRACTS.md` and `.terminus/agents/stage_contracts.json`;
4. resolve active task-format, complexity, runtime-authenticity, verifier and packaging validators/CI that enforce those rules;
5. resolve the creation profile, including whether `large_system_strict` applies and any explicitly justified narrower profile;
6. apply the control-plane precedence rule and stop with `POLICY_CONFLICT` if applicable authoritative sources cannot be reconciled.

The controller then provides a pinned `CREATION_RULE_CONTEXT` to every producer handoff containing at minimum:

```text
CONTROL_PLANE_COMMIT:
RULE_SOURCES:
ACTIVE_VALIDATORS:
CREATION_PROFILE:
NETWORK/ENVIRONMENT_CONSTRAINTS:
KNOWN_POLICY_CONFLICTS:
```

Downstream creators may read narrower role-specific policy as required, but they must not silently substitute a different repository rule baseline. Once task identity exists, persist the resolved context or an exact reference to it in the durable task session. If governing task rules materially change before freeze, rerun `RULE_RESOLUTION`, reconcile the delta and invalidate affected producer evidence before continuing.

## Strict large-system task model

For `large_system_strict`, numeric requirements are minimum floors/ranges that must emerge from a coherent production-style **engineering work package**. They are not quotas to manufacture against.

The default strict task is not one localized bug report transplanted into a large repository. Prefer substantial work such as feature/reliability completion, recovery implementation, migration completion, platform modernization, operability completion, security hardening, state-model rework, integration completion, or incident-driven remediation whose required end state spans multiple coupled responsibilities/invariants. An incident may motivate the work, but it should not be the sole source of difficulty.

- **At least 3,000 substantive, reachable solver-visible runtime/configuration LOC.** `3,000` is a floor, not a target or preferred proximity; naturally required systems may be 5,000, 10,000 or more substantive lines.
- The LOC floor must come from meaningful production/domain implementation. Duplicate, generated/vendor, dead/unreachable, unnecessary, boilerplate-only or micro-module-inflated code does not satisfy substantive scale.
- The system must exhibit production characteristics appropriate to its domain: differentiated responsibilities/modules, real runtime or operator entrypoints, realistic state/data, validation and error handling, configuration, operational workflows, meaningful inter-component coupling, and persistence/restart/recovery/idempotency/failure handling where applicable.
- Infrastructure tasks use **30–50** meaningful interacting resources when that scale is natural; decorative or copied resources do not count.
- Track **20–30** observable defect/incomplete-behavior manifestations derived from materially fewer root-cause clusters, with at least 15 manifestations participating in meaningful causal/interdependency relationships.
- Build **25–30 non-duplicative F2P behavioral cases organically** from materially distinct requirements, states, transitions, failure modes and interactions. Do not invent, split, rename, parameter-duplicate or weaken cases merely to reach the numeric range.
- Every F2P case must empirically starter/NOP-fail and Oracle-pass. Add P2P/regression cases according to actual preservation risk, not to inflate suite size.
- Include sufficient domain-relevant edge, boundary, negative and failure-path coverage. Negative cases remain F2P or P2P according to their starter-to-Oracle transition; they are not a third taxonomy.
- Edge/negative cases must exercise materially different invariants, boundaries, rejection/safety semantics, recovery behavior or operational transitions rather than duplicated happy paths with altered fixture values.

If this work-package scale, behavioral diversity, edge/failure coverage or production character cannot be reached naturally, return `SCENARIO_TOO_SMALL`. Never pad, silently downgrade, pile unrelated requirements together or build toward the numbers for their own sake.

## Instruction / documentation contract

The detailed authoritative instruction contract is `.terminus/agents/INSTRUCTION_POLICY.md`; the machine interface is stage `INSTRUCTION_DRAFT` in `.terminus/agents/stage_contracts.json`.

Edition 3 allows `instruction.md` to use **<=2 short paragraphs or <=20 concise bullets**. For a strict work package, the controller must allow enough concise bullets to state the complete material work request; brevity is not permission to omit requirements.

`instruction.md` must own:
- the engineering objective/change request;
- all material functional and operational requirements needed for a fair solve;
- material preservation, compatibility and safety requirements;
- required absolute output/artifact paths and exact structured-output schema where governing Edition 3 rules require them;
- concise references to solver-visible technical documentation.

Solver-visible documentation may own repository/folder/component layout, architecture/state models, runtime/operator entrypoints, schemas/record layouts, protocol semantics, API/CLI contracts and runbooks. It must not become a second prompt used to hide the task goal or material functional requirements outside `instruction.md` merely to evade the Edition 3 length limit.

The intended separation is:

`instruction = what must work -> docs/contracts = how the inherited system is organized/governed -> code/runtime = what exists now -> solver = identify implementation gaps and repair/complete them`

Do not require the instruction to narrate which internal component/function is incomplete or buggy. Such implementation diagnosis is normally solver work unless it would naturally be part of the engineering handoff and is independently supported by solver-visible evidence.

## Mandatory production-authenticity checks

For an operational/stateful strict task, before Instruction Writer or review:
1. Build a solver-visible **production evidence surface** when the work package asserts inherited operational/current-state facts: incident logs plus an independent handoff/state/operator artifact where appropriate.
2. Ground any current-state claims in those artifacts. Do not invent a “real-time” story or implementation diagnosis after the environment is built merely to make the prompt sound realistic.
3. Desired functional requirements are end-state requirements; they do not need to be presented as incident evidence.
4. For data-backed strict tasks, normally materialize **10,000–20,000** deterministic, varied primary business records.
5. Reject thin business logic. Major COBOL/business programs cannot be one constant output or one comparison surrounded by declarations; “one IF = one program” is a blocking authenticity smell.
6. Run `.terminus/validate_runtime_authenticity.py <task>` and treat failure as blocking.

## Role ownership

1. **Scenario Researcher** — engineering work-package candidates, objective/end state, requirement families, inherited system/state, persona, originality and scale fit; strict tasks must be more than a localized bug padded into a large environment.
2. **System Architect / Environment Builder** — runtime topology, representative state, solver-visible technical docs, operator evidence where appropriate and starter implementation; docs explain structure/contracts without leaking the repair plan.
3. **Defect Topology Designer** — private causal graph, strict manifestation connectivity, behavioral-surface breadth across normal/edge/negative/failure/recovery/cross-component behavior, and partial-fix traps; returns `SCENARIO_TOO_SMALL` when strict breadth would require padding.
4. **Reference Solution Author** — general deterministic repair/completion.
5. **Verifier Author** — behavioral F2P/P2P verifier from solver-visible requirements/contracts, including sufficient positive, edge, negative and failure-path scenarios according to operational risk.
6. **Human Writing Researcher** — public human-engineering calibration across substantial Jira/issues/change requests and incident handoffs; distinguishes required end state from evidence-backed current-state facts.
7. **Instruction Writer** — complete concise work request within the Edition 3 shape, normally up to 20 bullets where needed; states material functional requirements without implementation diagnosis or compressed hidden-test topology.
8. **Q1 Spec Gap Repairer** — closes legitimate graded behavior absent from solver-visible specification while preserving the instruction/documentation boundary and never omitting material requirements for brevity.
9. **Q2 Verifier Coverage Repairer** — adds behavioral coverage for material solver-visible requirements that are not tested.
10. **Q3 Spec Ambiguity Repairer** — resolves grading-relevant ambiguity without over-prescribing implementation.
11. **Documentation Writer** — reviewer-facing explanations without benchmark framing.
12. **Q7 Task Format Enforcer** — exact current folder/task.toml/Docker/verifier/solution/package conformance before expensive gates.
13. **Task Assembly Agent** — deterministic authoring checks, including instruction shape/completeness and instruction/docs boundary.
14. **Complexity Governor** — scale + authenticity adversarial review, including whether the task is a substantial coherent work package.
15. **Authoring Failure Diagnostician** — coarse deterministic failure routing.
16. **Q5 Oracle & Runtime Repair Specialist** — deep repair for Oracle/build/runtime/application/harness failures after evidence identifies the failing boundary.
17. **Q4 Spec-Test Contract Reviewer** — independent bidirectional spec/test/ambiguity review on the frozen candidate, including prompt-extension/spec-file loophole detection.
18. **Q6 Production Logic Auditor** — independent production-grade code/reachability/coupling review on the frozen candidate.
19. **Q8 Model Perspective Difficulty Simulator** — two diagnostic cold solve simulations after Pre-LLMaJ PASS; never official difficulty evidence.

The detailed expected input/output fields for these lifecycle stages are not duplicated here; they are resolved from `stage_contracts.json` at invocation time.

## Spec alignment state

`SPEC_ALIGNMENT` is producer-side and must finish before documentation/assembly:
- Q1 reports no unresolved material verifier->spec gap;
- Q2 reports no unresolved material spec->verifier gap;
- Q3 reports no unresolved grading-relevant ambiguity;
- `instruction.md` contains the complete material work request within the Edition 3 shape;
- referenced solver-visible docs remain legitimate technical documentation rather than a second prompt;
- instruction changes remain natural engineering request prose/bullets and do not mirror hidden tests.

These producers do not certify the result. Q4 performs the later independent contract review.

## Deterministic failure routing

On Oracle/build/runtime failure:
1. preserve run/job/artifact/log evidence;
2. use Authoring Failure Diagnostician for coarse ownership if needed;
3. invoke Q5 for deep `ENVIRONMENT | BUILD | DEPENDENCY | STARTUP | STATE | APPLICATION | ORACLE | VERIFIER_HARNESS | INFRASTRUCTURE | CONTRACT` diagnosis;
4. repair only the smallest coherent responsible layer;
5. never weaken a legitimate verifier requirement merely to obtain reward 1.

## Freeze conditions

`FROZEN_CANDIDATE` requires:
- current creation-rule context reconciled against governing task rules;
- all required registered creation-stage inputs/outputs/evidence current through `DETERMINISTIC_VALIDATION`;
- Q1/Q2/Q3 producer alignment complete with no unresolved material gap/ambiguity;
- Q7 current exact-format check PASS;
- structure/static/lint PASS;
- complexity gate PASS;
- runtime-authenticity PASS;
- for `large_system_strict`, a substantial coherent engineering work package rather than one localized bug padded into scale;
- substantive reachable production/domain LOC >=3,000 for `large_system_strict`, treated as a floor rather than a target;
- no material LOC/resource/test padding or duplication used to satisfy numeric constraints;
- sufficient distinct normal, edge, boundary, negative and failure-path behavioral coverage for the operational contract;
- `instruction.md` satisfies the Edition 3 <=2-paragraph/<=20-bullet shape and contains all material functional/operational requirements;
- solver-visible docs provide legitimate architecture/schema/protocol/runbook context without hiding task goals/material requirements or leaking the repair plan;
- production evidence surface PASS when current-state operational claims are made;
- representative state-volume PASS when applicable;
- Oracle reward 1;
- NOP reward 0;
- every planned F2P Oracle-pass/starter-fail;
- intended P2P preserved;
- no solution/test leakage.

## Quality interlock

A frozen candidate does not begin normal Pre-LLMaJ until stage `QUALITY_INTERLOCK` is satisfied:
- Q4 Spec-Test Contract Reviewer returns packet-bound `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT`;
- Q6 Production Logic Auditor returns packet-bound `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT`;
- both reviews satisfy current exact-commit/scope-freshness rules.

If either returns REVISE, route findings to the smallest responsible producer, invalidate affected evidence, and rerun the quality interlock. A creator cannot convert its own evidence into independent review approval.
