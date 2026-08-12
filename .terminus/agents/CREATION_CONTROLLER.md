# Terminus Edition 3 Creation Controller

Policy version: `1.0`

This controller is mandatory for new/rebuilt tasks. Current Edition 3 rules override local policy on conflict. Every creation run also applies `.terminus/agents/PRODUCTION_AUTHENTICITY.md` and the additive quality interlock in `.terminus/agents/QUALITY_AGENT_REGISTRY.md`.

## States

`CREATION_REQUEST -> RULE_RESOLUTION -> IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT -> DOCUMENTATION_DRAFT -> FORMAT_GATE -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK`

`BLOCKED` may overlay any state.

## Creation bootstrap / rule resolution

No producer starts scenario design until the controller has resolved one creation-rule context for the run.

At `RULE_RESOLUTION`, the controller must:
1. resolve the exact control-plane commit used for creation;
2. read the current repository-wide task rules in `TERMINUS_3_AI_INSTRUCTIONS.md`;
3. read `.terminus/reviewers/REVIEWER_CHECKLIST.md`, `.terminus/agents/CREATION_PIPELINE.md`, `.terminus/agents/PRODUCTION_AUTHENTICITY.md` and `.terminus/agents/QUALITY_AGENT_REGISTRY.md`;
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

## Strict large-system constraints

For `large_system_strict`, numeric requirements are minimum floors/ranges that must emerge from a coherent production-style system and incident. They are not quotas to manufacture against.

- **At least 3,000 substantive, reachable solver-visible runtime/configuration LOC.** `3,000` is a floor, not a target or preferred proximity; naturally required systems may be 5,000, 10,000 or more substantive lines.
- The LOC floor must come from meaningful production/domain implementation. Duplicate, generated/vendor, dead/unreachable, unnecessary, boilerplate-only or micro-module-inflated code does not satisfy substantive scale.
- The system must exhibit production characteristics appropriate to its domain: differentiated responsibilities/modules, real runtime or operator entrypoints, realistic state/data, validation and error handling, configuration, operational workflows, meaningful inter-component coupling, and persistence/restart/recovery/idempotency/failure handling where applicable.
- Infrastructure tasks use **30–50** meaningful interacting resources when that scale is natural; decorative or copied resources do not count.
- Track **20–30** observable defect manifestations derived from materially fewer root-cause clusters, with at least 15 manifestations participating in meaningful causal/interdependency relationships.
- Build **25–30 non-duplicative F2P behavioral cases organically** from materially distinct requirements, states, transitions, failure modes and interactions. Do not invent, split, rename, parameter-duplicate or weaken cases merely to reach the numeric range.
- Every F2P case must empirically starter/NOP-fail and Oracle-pass. Add P2P/regression cases according to actual preservation risk, not to inflate suite size.
- Include sufficient domain-relevant edge, boundary, negative and failure-path coverage. Negative cases remain F2P or P2P according to their starter-to-Oracle transition; they are not a third taxonomy.
- Edge/negative cases must exercise materially different invariants, boundaries, rejection/safety semantics, recovery behavior or operational transitions rather than duplicated happy paths with altered fixture values.

If this scale, behavioral diversity, edge/failure coverage or production character cannot be reached naturally, return `SCENARIO_TOO_SMALL`. Never pad, silently downgrade or build toward the numbers for their own sake.

## Mandatory production-authenticity checks

For an operational/stateful strict task, before Instruction Writer or review:
1. Build a solver-visible **production evidence surface**: incident logs plus an independent handoff/state/operator artifact.
2. Ensure incident prose is grounded in those artifacts. Do not invent a “real-time” story after the environment is built.
3. For data-backed strict tasks, normally materialize **10,000–20,000** deterministic, varied primary business records.
4. Reject thin business logic. Major COBOL/business programs cannot be one constant output or one comparison surrounded by declarations; “one IF = one program” is a blocking authenticity smell.
5. Run `.terminus/validate_runtime_authenticity.py <task>` and treat failure as blocking.

## Role ownership

1. **Scenario Researcher** — incident candidates, evidence surface, persona, normal workflow, originality and scale fit.
2. **System Architect / Environment Builder** — runtime topology, representative state, logs/operator evidence, starter implementation.
3. **Defect Topology Designer** — private causal graph and partial-fix traps.
4. **Reference Solution Author** — general deterministic repair.
5. **Verifier Author** — behavioral F2P/P2P verifier from solver-visible contract, including sufficient positive, edge, negative and failure-path scenarios according to operational risk.
6. **Human Writing Researcher** — public human-engineering calibration and task-specific writing profile.
7. **Instruction Writer** — evidence-backed handoff, not compressed rubric.
8. **Q1 Spec Gap Repairer** — closes legitimate graded behavior absent from solver-visible specification using natural invariant-level prose/contracts.
9. **Q2 Verifier Coverage Repairer** — adds behavioral coverage for material solver-visible requirements that are not tested.
10. **Q3 Spec Ambiguity Repairer** — resolves grading-relevant ambiguity without over-prescribing implementation.
11. **Documentation Writer** — reviewer-facing explanations without benchmark framing.
12. **Q7 Task Format Enforcer** — exact current folder/task.toml/Docker/verifier/solution/package conformance before expensive gates.
13. **Task Assembly Agent** — deterministic authoring checks.
14. **Complexity Governor** — scale + authenticity adversarial review.
15. **Authoring Failure Diagnostician** — coarse deterministic failure routing.
16. **Q5 Oracle & Runtime Repair Specialist** — deep repair for Oracle/build/runtime/application/harness failures after evidence identifies the failing boundary.
17. **Q4 Spec-Test Contract Reviewer** — independent bidirectional spec/test/ambiguity review on the frozen candidate.
18. **Q6 Production Logic Auditor** — independent production-grade code/reachability/coupling review on the frozen candidate.
19. **Q8 Model Perspective Difficulty Simulator** — two diagnostic cold solve simulations after Pre-LLMaJ PASS; never official difficulty evidence.

## Spec alignment state

`SPEC_ALIGNMENT` is producer-side and must finish before documentation/assembly:
- Q1 reports no unresolved material verifier->spec gap;
- Q2 reports no unresolved material spec->verifier gap;
- Q3 reports no unresolved grading-relevant ambiguity;
- any instruction change remains natural engineer handoff prose and does not mirror tests.

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
- Q1/Q2/Q3 producer alignment complete with no unresolved material gap/ambiguity;
- Q7 current exact-format check PASS;
- structure/static/lint PASS;
- complexity gate PASS;
- runtime-authenticity PASS;
- substantive reachable production/domain LOC >=3,000 for `large_system_strict`, treated as a floor rather than a target;
- no material LOC/resource/test padding or duplication used to satisfy numeric constraints;
- sufficient distinct normal, edge, boundary, negative and failure-path behavioral coverage for the operational contract;
- production evidence surface PASS when applicable;
- representative state-volume PASS when applicable;
- Oracle reward 1;
- NOP reward 0;
- every planned F2P Oracle-pass/starter-fail;
- intended P2P preserved;
- no solution/test leakage.

## Quality interlock

A frozen candidate does not begin normal Pre-LLMaJ until:
- Q4 Spec-Test Contract Reviewer returns packet-bound `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT`;
- Q6 Production Logic Auditor returns packet-bound `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT`;
- both reviews apply to the exact task commit.

If either returns REVISE, route findings to the smallest responsible producer, invalidate affected evidence, and rerun the quality interlock. A creator cannot convert its own evidence into independent review approval.
