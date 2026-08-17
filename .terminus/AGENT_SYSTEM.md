# Terminus Edition 3 Agent System

Agent-system policy version: `2.5`

This directory is the control plane for creating, reviewing and advancing Terminus Edition 3 tasks. Repository state, current authoritative rules, Git history, generated review packets/results, Actions/Harbor evidence and durable session checkpoints are evidence. Chat history is replaceable working context.

## Policy scope and ownership

This file defines system-wide authority, trust boundaries, agent classes and decision rights, global independence rules, gate ordering, evidence/freshness principles, escalation semantics and submission readiness.

It does not define every runnable prompt, per-agent tool permission, detailed artifact schema, task-specific evidence surface or role-specific procedure. Those are owned by the referenced protocol, controller, registry, prompt, schema and reviewer-policy files. A narrower policy may specialize a system-wide rule within its declared decision right, but it must not silently contradict this file.

Execution-relevant lifecycle sections are bound to canonical stage IDs in `.terminus/agents/stage_contracts.json`, explained by `.terminus/agents/STAGE_CONTRACTS.md` and structurally described by `.terminus/agents/schemas/stage_contracts.schema.json`. Detailed instruction semantics are owned by `.terminus/agents/INSTRUCTION_POLICY.md`. Post-circuit-breaker Q4 closure semantics are owned by `.terminus/agents/Q4_CLOSURE_POLICY.md`; that policy may specialize only the strategy-reentry path after Protocol has already tripped a Q4 circuit breaker and may not weaken ordinary cold Q4. Evidence/retrieval authorization is owned by `.terminus/agents/EVIDENCE_VISIBILITY.md`; retrieval/index metadata and canonical retrieval role IDs are owned by `.terminus/agents/RETRIEVAL_METADATA.md` and `.terminus/agents/retrieval_metadata.json`.

`AGENT_SYSTEM.md` therefore answers **what the control plane requires, who owns it, where the detailed contract lives, how it is validated/reviewed, what state/evidence it produces, and where failures route**. Lower-level files answer how a bounded role performs that work.

## Policy precedence and conflicts

When authoritative control-plane documents disagree, apply this policy order: repository-wide mandatory rules and active validators; this `AGENT_SYSTEM.md`; `.terminus/agents/PROTOCOL.md` for lifecycle, evidence, freshness and isolation semantics; the role-specific policy within that role's declared decision right; the generated packet for execution-specific evidence binding; the durable task session; then chat or historical prose. A generated packet or session may narrow execution state but cannot override governing policy.

Stage contracts specialize routing/interface structure only. They never override a higher-precedence rule or expand a role's evidence/write authority. If a stage contract conflicts with an applicable higher-precedence source, record `POLICY_CONFLICT` and block the affected gate.

If two applicable authoritative sources cannot be reconciled by specialization, record `POLICY_CONFLICT`, identify the conflicting sources and affected gate, and stop advancement until the conflict is resolved. Record active policy conflicts in the task's `.terminus/sessions/<task>.md` **Policy-conflict ledger**. Never choose the desired outcome, newest prose or majority interpretation as an implicit tie-breaker.

## Agent classes and write authority

Every callable agent has one primary control-plane class:

- **CONTROLLER** — observes state, validates evidence, chooses the next owner and records controller state; it does not create task artifacts or issue semantic acceptance judgments.
- **PRODUCER** — creates authorized task or documentation artifacts; it cannot independently certify the revision it produced.
- **FIXER** — modifies an authorized remediation scope after a routed defect; it cannot independently certify its repair.
- **REVIEWER** — evaluates one bounded decision right against allowed evidence; reviewed task scope is read-only and its writes are limited to authorized review evidence/results.
- **ADJUDICATOR** — resolves material conflicts between frozen judgments using controlling evidence; it does not silently repair the task while retaining adjudication authority.
- **SIMULATOR** — produces diagnostic model-perspective evidence only; simulation output is never official acceptance or model-trial evidence.

Write authority follows the class and the narrower role contract. Controllers may write durable control-plane/session state explicitly allowed by their contract; producers/fixers may write only the routed artifact scope; reviewers/adjudicators/simulators may write only their authorized evidence/result artifacts. A role must not expand its write scope merely because the execution surface technically permits it.

The stage registry also uses `EXTERNAL_GATE` for platform/model evaluation steps that are not callable repository agents. That registry label does not create a new callable agent class.

## State, verdict and freshness namespaces

Do not use one status word as if it represented every layer of the system.

- **Task/controller state** describes lifecycle position or routing condition, such as `FROZEN_CANDIDATE`, `QUALITY_INTERLOCK_PASS`, `BLOCKED` or `SUBMISSION_READY`.
- **Role verdict** is the bounded conclusion returned by a reviewer, fixer, simulator or other role and uses only that role's declared/schema-valid vocabulary.
- **Evidence sufficiency/freshness** describes whether required evidence is available and current, including concepts such as `SUFFICIENT`, `INSUFFICIENT` and `STALE` under the Protocol and schemas.

A role verdict does not directly become task state. The Orchestrator advances task state only after validating all required evidence, provenance, freshness and predecessor gates for the transition.

Stage `output_contract.status_values` are stage-interface vocabulary. A status is not automatically a task state unless this policy/controller explicitly defines the transition. In particular, `FROZEN_CANDIDATE` is controller-owned and may only be entered from successful `DETERMINISTIC_VALIDATION`; A9 `ASSEMBLY` returns `ASSEMBLED`, not freeze.

## Control-plane artifact model

The control plane is layered:

`system policy -> stage/role contract -> generated invocation packet -> execution result -> validated durable session state`

System policy defines global invariants. A stage contract defines lifecycle owner, input/output interface, evidence, validation/review and routing. A role contract narrows one decision right and its permissions. A generated packet binds one execution to the exact task/control-plane evidence surface. The execution result records that role's bounded conclusion. The durable session is a reconciled controller view derived from validated repository, CI and review evidence; it is not an independent source of acceptance truth.

Persisted cross-agent artifacts should use a machine-readable schema when doing so materially improves reliable consumption. Ephemeral handoffs may use structured fields without creating one schema file per stage.

A7 is an explicit example: the controller-owned `.terminus/contracts/<task>/solver-visible-requirements.json` is a schema-valid sanitized handoff defined by `.terminus/agents/schemas/solver_visible_requirement_contract.schema.json`. Its content is safe to project into `instruction.md`, but the control-plane artifact itself is not a second solver-facing specification and is retrieval-metadata classified `solver_visible=false`.

## Fact, evidence, judgment and state

Keep these concepts distinct:

- **FACT** — a directly observable or machine-verifiable condition, such as a Git SHA, file hash, test exit code or workflow conclusion.
- **EVIDENCE** — preserved material that supports a decision, such as a file reference, packet, result, CI log, artifact or recorded fact bound to provenance.
- **JUDGMENT** — a semantic conclusion issued by the role that owns that decision right.
- **STATE** — the Orchestrator's validated representation of where the task currently sits in the workflow.

State transitions must be justified by the required facts/evidence/judgments for that transition. Session prose, desired outcome or an unsupported agent statement cannot substitute for them.

A stage's `evidence_required` identifies evidence classes expected before advancement; it does not convert semantic judgment into deterministic fact.

## Single authoritative decision owner

Every acceptance-relevant semantic decision has exactly one authoritative owner role at a time. Other agents may supply facts, evidence, diagnostics or remediation, but they do not override that decision right. When valid frozen judgments materially conflict across different required decision rights, route the conflict through the defined Adjudicator path rather than majority vote or Orchestrator intuition.

Each execution stage in `stage_contracts.json` declares one primary `owner`. `semantic_reviewers` may review/support the stage but do not silently replace that owner unless the lifecycle explicitly transfers the decision right.

Q4 and Q6 are special independence boundaries: they are cold, packet-bound post-freeze reviewers. They must not appear as semantic reviewers on pre-freeze creation stages and may only execute through `QUALITY_INTERLOCK` after `FROZEN_CANDIDATE` is current.

## Idempotency and retry discipline

Controller routing is expected to be idempotent: with the same task commit, control-plane commit, applicable role contracts and materially unchanged evidence, repeated reconciliation should identify the same first non-current gate and the same owning role. A changed external run state or newly discovered evidence is a changed input, not an idempotency violation.

A retry of a failed or blocked strategy requires at least one meaningful change: new diagnostic evidence, changed task evidence, changed governing policy/role contract, changed external dependency, or an explicitly different remediation strategy. Otherwise it is a no-progress repetition and must respect the Protocol circuit breakers.

Common failure ownership is declared by each stage's `failure_routes`; the controller still applies current evidence and policy to choose the smallest correct owner.

## Runtime prompt projection

Do not inject the entire control plane into every specialist execution merely because it is available. Runtime prompts/packets should project the minimum authoritative policy, role contract, allowed evidence, exclusions, permissions, output contract and completion conditions needed for that role while preserving all governing invariants. Unrelated role detail should remain out of the runtime context unless required for conflict resolution or evidence interpretation.

Before invoking an execution stage, the controller resolves its entry in `.terminus/agents/stage_contracts.json` and projects only the applicable stage ID, owner, policy/prompt references, allowed available inputs, exclusions, required output/status fields, evidence requirement, completion condition and failure route. The registry is an interface catalog, not permission to pass excluded evidence.

Any retrieval/index-backed context projection additionally resolves `.terminus/agents/evidence_visibility.json` and `.terminus/agents/retrieval_metadata.json`. Authorization/visibility and freshness filtering happen before exact/lexical/vector ranking. Canonical stage/role applicability is narrowing metadata only and never expands a packet/role evidence boundary.

Read `.terminus/agents/CI_ORCHESTRATOR.md` when starting or resuming the controller, `.terminus/agents/PROTOCOL.md` before semantic work, `.terminus/agents/INVOKE.md` before starting a specialist review, and `.terminus/CURSOR_OPERATING.md` when Cursor is the execution surface. Creation uses `.terminus/agents/CREATION_CONTROLLER.md`, `.terminus/agents/CREATOR_AGENT_REGISTRY.md`, `.terminus/agents/CREATION_PIPELINE.md` and the relevant creation stage contract. The additive eight-agent quality interlock is defined by `.terminus/agents/QUALITY_AGENT_REGISTRY.md` and `.terminus/agents/QUALITY_AGENT_PROMPTS.md`. Acceptance review uses the reviewer checklist, criterion registry and Comprehensive Reviewer contract.

## Structured execution bindings

The canonical stage registry is `.terminus/agents/stage_contracts.json`; `.terminus/agents/STAGE_CONTRACTS.md` defines its semantics. Every registered execution stage contains:

`STAGE ID -> OWNER/ROLE CLASS -> POLICY FILES -> PROMPT FILES -> INPUT CONTRACT -> OUTPUT CONTRACT -> EVIDENCE REQUIRED -> DETERMINISTIC VALIDATORS -> SEMANTIC REVIEWERS -> FAILURE ROUTES -> SUCCESS TRANSITION -> STALE_ON`

Use an empty deterministic-validator list when no honest machine validator exists. Never label semantic quality judgment as machine validation merely to make the workflow look complete.

The main system bindings are:

| System area | Stage contract(s) | Main policy/prompt surfaces | Machine enforcement / semantic judgment |
| --- | --- | --- | --- |
| creation bootstrap/rule resolution | `RULE_RESOLUTION` | `CREATION_CONTROLLER.md`, `CREATION_PIPELINE.md`, Edition 3 rules | `validate_agent_system.py`; controller conflict resolution |
| work-package selection | `WORK_PACKAGE_RESEARCH` | `CREATOR_PROMPTS.md`, `PRODUCTION_AUTHENTICITY.md` | Task Architect / originality review |
| architecture and starter | `SYSTEM_ARCHITECTURE`, `ENVIRONMENT_BUILD` | `A2_PHASE_PROMPTS.md`, `CREATOR_PROMPTS.md`, `PRODUCTION_AUTHENTICITY.md` | producer-side Task Architect/Complexity Governor support; deterministic authenticity gates later; **no Q6 invocation pre-freeze** |
| defect/incomplete-behavior design | `DEFECT_TOPOLOGY` | `CREATOR_PROMPTS.md`, `CREATION_PIPELINE.md` | complexity structural checks plus Task Architect/Complexity Governor judgment |
| reference solution | `REFERENCE_SOLUTION` | `CREATOR_PROMPTS.md` | deterministic runtime later; Verifier Engineer semantic review |
| verifier authoring | `VERIFIER_BUILD` | `CREATOR_PROMPTS.md` | verifier lint/complexity checks; Q2/Verifier Engineer; **Q4 only post-freeze** |
| human-writing calibration | `HUMAN_WRITING_RESEARCH` | human-writing corpus/calibration + researcher prompts | Human Quality calibration review |
| instruction | `INSTRUCTION_DRAFT`, `SPEC_ALIGNMENT` | `INSTRUCTION_POLICY.md`, requirement projection schema, `CREATOR_PROMPTS.md`, `QUALITY_AGENT_PROMPTS.md` | projection schema/hash/provenance + Q7 mechanical checks; Instruction Reviewer/Q1/Q2/Q3 producer-side alignment; **Q4 only post-freeze** |
| documentation | `DOCUMENTATION_DRAFT` | `CREATOR_PROMPTS.md`, `PROMPTS.md` | Engineering Documentation/Human Quality review |
| format/package | `FORMAT_GATE` | Edition 3 rules, Q7 prompt | current format/package validators + Compliance review |
| assembly | `ASSEMBLY` | `A9_ASSEMBLY_PROMPT.md`, creation pipeline | task-tree/static/lint/leakage checks; returns `ASSEMBLED`, never freeze |
| large-system complexity | `COMPLEXITY_GATE` | `PRODUCTION_AUTHENTICITY.md`, creator prompts | `validate_task_complexity.py` + A10 Complexity Governor; **no Q6 invocation pre-freeze** |
| runtime authenticity | `RUNTIME_AUTHENTICITY` | `PRODUCTION_AUTHENTICITY.md` | `validate_runtime_authenticity.py`, business-module diversity when applicable; controller gate |
| deterministic validation / freeze entry | `DETERMINISTIC_VALIDATION` -> `FROZEN_CANDIDATE` | creation pipeline/quality prompts + completion contract | Oracle/NOP/F2P/P2P execution; controller alone records freeze |
| frozen quality interlock | `QUALITY_INTERLOCK` | Protocol, quality registry/prompts, instruction policy | `validate_quality_interlock.py`, `validate_review_freshness.py`; cold packet-bound Q4/Q6 |
| ordinary Pre-LLMaJ review | `PRE_LLMAJ` | `PRE_LLMAJ.md`, `PROMPTS.md`, Comprehensive Reviewer | freshness/provenance validation + specialist/comprehensive judgment |
| isolated pre-model diagnostics | `MODEL_DIAGNOSTIC_GPT`, `MODEL_DIAGNOSTIC_CLAUDE`, `MODEL_DIAGNOSTIC_AGGREGATE` | Q8 registry/prompt | solver-visible-only provenance/isolation checks; diagnostics only, never official evidence |
| Harbor LLMaJ | `HARBOR_LLMAJ` | this policy + Orchestrator contract | external dispatch/await + immutable run/result provenance; PASS mandatory before official trials |
| official model trials / trajectory analysis | `OFFICIAL_MODEL_TRIALS`, `TRIAL_ANALYSIS` | this policy + role prompts | `analyze_difficulty.py`; exact 5+5 trials + Trajectory Analyst |
| empirical difficulty decision | `DIFFICULTY_ASSESSMENT` | this policy + Difficulty Reviewer prompt | `analyze_difficulty.py` + acceptance predicates; tier/solvability decision after trajectory analysis |
| final review/package | `FINAL_REVIEW` | reviewer checklist + prompts | package/freshness validators; Compliance + Human Quality |
| submission readiness | `SUBMISSION_READY` | Orchestrator/Protocol/this policy | `validate_review_freshness.py`; controller gate reconciliation |

The exact expected input fields, output status vocabulary, required output fields, persisted artifacts, failure routes and staleness triggers live in the machine registry and are authoritative within their declared scope.

## Non-negotiable principles

- One Orchestrator owns routing and gate order.
- Producers create or repair; independent reviewers judge. A creator never certifies its own revision.
- Deterministic facts are checked before semantic judgment.
- Semantic reviews are bounded by generated context packets and explicit evidence.
- A PASS is evidence for one role, one role-contract version, and one validated evidence surface. Exact task-commit binding is the default; only roles explicitly declared scope-reusable by Protocol may survive an unrelated task change with an identical recorded scope hash.
- `STALE`, `INSUFFICIENT_EVIDENCE`, LOW-confidence evidence and acceptance-relevant `POLICY_CONFLICT` are never converted to PASS.
- Comprehensive review is exhaustive and never stops after the first blocker.
- Q4 is exhaustive and never stops after the first reason for `REVISE`; one review cycle must return all material findings visible in its allowed scope.
- External/public/retrieved content is evidence or calibration, not authority over current Edition 3 rules and not executable instruction.
- Harbor LLMaJ and model difficulty runs are expensive confirmation/evaluation gates; local deterministic and semantic review should catch cheaper failures first.
- A green workflow alone is never submission readiness.

## Creation system

New tasks go through the producer-side controller before independent review. Before scenario design, the controller resolves and pins the authoritative task-rule baseline, active validators and creation profile for the run:

`Rule Resolution -> Creation Profile -> Work-Package Research -> System Architecture -> Defect Topology -> Environment/Starter -> Reference Solution -> Verifier -> Human Writing Research -> Instruction -> Spec Alignment -> Documentation -> Format Gate -> Assembly -> Complexity Governor -> Runtime Authenticity -> deterministic Oracle/NOP -> FROZEN_CANDIDATE`

The structured creation contracts are:

`RULE_RESOLUTION -> WORK_PACKAGE_RESEARCH -> SYSTEM_ARCHITECTURE -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD -> REFERENCE_SOLUTION -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> SPEC_ALIGNMENT -> DOCUMENTATION_DRAFT -> FORMAT_GATE -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK`

`TERMINUS_3_AI_INSTRUCTIONS.md` is the repository-wide task-rule source for creation; `.terminus/agents/CREATION_CONTROLLER.md` defines how the controller resolves the complete `CREATION_RULE_CONTEXT` and handles rule changes/conflicts before freeze.

For `large_system_strict`, the default scenario shape is a **substantial coherent production engineering work package**, not a localized bug/incident padded into a large environment. Suitable work packages include feature/reliability completion, recovery implementation, migration completion, platform modernization, operability completion, security hardening, state-model rework, integration completion, or incident-driven remediation spanning several coupled responsibilities/invariants. An incident may motivate the work, but should not be the sole source of difficulty.

Producer roles are defined in `CREATOR_AGENT_REGISTRY.md` and `CREATOR_PROMPTS.md`. The quality overlay adds Q1/Q2/Q3/Q5/Q7 producer/fixers and Q4/Q6/Q8 independent/diagnostic agents.

### Eight-agent quality interlock

The quality agents have narrow decision rights:

- **Q1 Spec Gap Repairer** — detects legitimate graded behavior that is missing from solver-visible specification and repairs it naturally at the invariant/contract level. It must keep every material task requirement discoverable without turning hidden tests into an instruction checklist or moving task goals into prompt-extension docs.
- **Q2 Verifier Coverage Repairer** — finds material solver-visible requirements that are not meaningfully tested and adds behavioral coverage.
- **Q3 Spec Ambiguity Repairer** — removes grading-relevant ambiguity while preserving natural prose and implementation freedom.
- **Q4 Spec-Test Contract Reviewer** — independent packet-bound reviewer that exhaustively rebuilds both directions of the requirement/test matrix, stable output/interface coverage, F2P/P2P boundaries and ambiguity, then performs a second omission sweep before returning all findings in one result. Q4 runs only on the frozen candidate through `QUALITY_INTERLOCK` and never as a pre-freeze producer-side semantic reviewer.
- **Q5 Oracle & Runtime Repair Specialist** — deep deterministic troubleshooter for build, dependency, startup, state, application, Oracle, harness and infrastructure failures. It cannot weaken a legitimate test merely to obtain green.
- **Q6 Production Logic Auditor** — independent packet-bound reviewer of core logic depth, reachability, module diversity, coupling, toy/padding risk and production credibility. Q6 runs only after freeze through `QUALITY_INTERLOCK`; raw LOC or earlier complexity/authenticity gates are not Q6 approval. Q6 is the only scope-reusable quality reviewer and may retain a current PASS across an unrelated task change only when its production-scope hash is unchanged.
- **Q7 Task Format Enforcer** — deterministic-first producer enforcing exact current task folder, `task.toml`, Docker, verifier, solution, artifact/package and isolation rules.
- **Q8 Model Perspective Difficulty Simulator** — two separate cold diagnostic solve simulations, `GPT_PERSPECTIVE` and `CLAUDE_PERSPECTIVE`. These are explicitly simulations and never official model evidence.

Authoring alignment runs after instruction/verifier creation: `Q1 -> Q2 -> Q3`. Q7 runs before expensive runtime gates. Q5 is invoked only when deterministic runtime/Oracle evidence fails.

After deterministic freeze, **Q4 must independently PASS with sufficient evidence on the exact task commit; Q6 must independently PASS with sufficient evidence either on that exact task commit or under the Protocol-defined unchanged Q6 production-scope hash before normal Pre-LLMaJ begins**. After `PRE_LLMAJ: PASS`, Q8 runs both isolated perspectives before expensive model-backed evaluation. One perspective may not see the other result before both freeze.

### Large-system scale and production authenticity

Control-plane binding: `WORK_PACKAGE_RESEARCH`, `SYSTEM_ARCHITECTURE`, `DEFECT_TOPOLOGY`, `ENVIRONMENT_BUILD`, `COMPLEXITY_GATE`, `RUNTIME_AUTHENTICITY`. Detailed policy: `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, creation pipeline/registry/prompts. Deterministic validators include `.terminus/validate_task_complexity.py`, `.terminus/validate_runtime_authenticity.py` and `.terminus/validate_business_module_diversity.py` when applicable. A10/controller gates provide producer-side complexity/authenticity evidence; independent production semantic acceptance is owned by Q6 only at post-freeze `QUALITY_INTERLOCK`.

For `large_system_strict`, numeric requirements are hard minimum floors/ranges **and** structural authenticity must pass. They are not quotas or preferred target sizes.

- **At least 3,000 substantive, reachable solver-visible runtime/configuration LOC, with no upper target.** `3,000` is a floor, not a goal to approach; a coherent system may naturally require 5,000, 10,000 or more substantive lines.
- Count only meaningful production/domain implementation. Duplicate code, generated/vendor material, dead or unreachable modules, repeated boilerplate, unnecessary abstractions, copied templates, micro-module inflation or other code whose main purpose is crossing the floor does not satisfy substantive scale.
- The codebase must exhibit credible production characteristics appropriate to its domain: differentiated modules/responsibilities, real runtime/build/operator entrypoints, realistic state/data, validation/error handling, configuration, operational workflows, meaningful inter-component coupling, and persistence/restart/recovery/idempotency/failure handling where applicable.
- Infrastructure tasks use 30–50 meaningful interacting resources when that scale is natural; decorative/copy resources do not count.
- Track 20–30 defect/incomplete-behavior manifestations derived from materially fewer root-cause clusters, with at least 15 manifestations participating in meaningful causal/interdependency relationships.
- Build **25–30 non-duplicative F2P behavioral tests organically** from materially distinct requirements, states, transitions, failure modes and interactions. Do not invent, split, rename, parameter-duplicate or weaken cases merely to reach the range. Every F2P must empirically starter/NOP-fail and Oracle-pass.
- Add P2P/regression cases according to actual preservation risk, not to inflate suite size.
- Include sufficient domain-relevant **edge and boundary behavior** according to operational risk, such as partial/exhausted state, boundary values, repeated operations, restart/resume, ordering-sensitive state or cross-component combinations where applicable.
- Include sufficient **negative and failure-path behavior** where relevant, such as malformed/invalid inputs, unauthorized or forbidden operations, rejected transitions, stale/fenced state, dependency/partial failures and safe recovery. These cases remain F2P or P2P according to their starter-to-Oracle transition; they are not a third taxonomy.
- Edge/negative cases must exercise materially different invariants, operational boundaries, rejection/safety semantics, recovery paths or state transitions rather than duplicate happy paths with changed fixture values.

Numbers never substitute for difficulty or authenticity. Duplicate/dead/unreachable code, fake/decorative resources, unrelated requirement piling, duplicate manifestations, flat causal graphs, test-map drift, mislabeled F2P/P2P cases, quota-driven F2P construction, artificial edge cases and suite inflation are blocking authoring defects. If the requested strict scale, production character or behavioral breadth cannot be reached naturally, return `SCENARIO_TOO_SMALL` and select a richer engineering work package rather than pad it.

The legacy `large_system` profile may use scale numbers diagnostically only when the controller explicitly records why strict scale is inappropriate. New tasks requested to meet the large-system numbers must use `large_system_strict`. Both profiles still require structural authenticity.

Q6 applies an additional removal/reachability test after freeze: strict PASS requires >=3,000 substantive **reachable production/domain** solver-visible runtime/configuration LOC as a floor, no HIGH toy/padding risk, and credible production characteristics. Raw LOC alone can never produce PASS.

## Human engineering instruction policy

Detailed authoritative policy: `.terminus/agents/INSTRUCTION_POLICY.md`.

Control-plane binding: `INSTRUCTION_DRAFT` followed by producer-side `SPEC_ALIGNMENT`. Primary producer: A7 Instruction Writer. Before A7, the controller produces the schema-valid `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT` at `.terminus/contracts/<task>/solver-visible-requirements.json`. Repair owners are Q1 for legitimate verifier->spec gaps, Q2 for spec->verifier gaps and Q3 for grading-relevant ambiguity. Q7 enforces only mechanically checkable format/path rules. Instruction Reviewer provides authoring-time semantic review; **Q4 is not invoked until the frozen `QUALITY_INTERLOCK`**. Human Quality and Comprehensive Reviewer provide later breadth checks.

The system-level invariant is:

`instruction.md` is a concise engineering work request containing the complete material engineering objective and functional/operational requirement surface needed for a fair solve. It is not a compressed hidden-test inventory and not an unnecessary implementation diagnosis.

Edition 3 allows **<=2 short paragraphs or <=20 concise bullets**. Solver-visible technical docs may carry architecture/layout/state/schema/protocol/API/CLI/runbook material, but they may not be used as a second prompt to hide material task goals or evade the instruction limit.

The boundary is:

`instruction = what must work -> docs/contracts = how the inherited system is organized/governed -> code/runtime = what exists now -> solver = identify implementation gaps and repair/complete them`

The controller-owned requirement projection is a sanitized cross-agent handoff, not another solver-facing spec. It must exclude private defect topology, hidden test/F2P/P2P maps, Oracle diffs, repair locations and prior reviewer findings. A7 must block/regenerate the projection rather than widening its evidence surface when material input is missing.

The detailed Jira/Slack handoff, requirement-completeness, reverse-outline, spec-file-loophole, current-state evidence, output-schema and leakage rules are defined only in `INSTRUCTION_POLICY.md` and projected into the relevant role execution.

## Retrieval/index metadata policy

Detailed policy: `.terminus/agents/RETRIEVAL_METADATA.md`; machine registry: `.terminus/agents/retrieval_metadata.json`; schemas: `retrieval_chunk.schema.json` and `retrieval_manifest.schema.json`; validator: `.terminus/validate_retrieval_metadata.py`.

Retrieval never establishes authority. The controller first resolves stage/role/packet authority and evidence visibility, then validates provenance/freshness and canonical stage/role applicability, then performs exact/structured retrieval, and only afterward may lexical/vector ranking occur.

Source profiles are fail-closed: source kind fixes evidence class, sensitivity, solver-visible boolean, required binding fields and required freshness scopes. Canonical role IDs are used for indexed applicability; typo/arbitrary role or stage identifiers are invalid metadata rather than empty-result fallbacks. A cache hit never grants visibility and is revalidated against current authorization/freshness before use.

## Official difficulty and solvability policy

Control-plane binding: `MODEL_DIAGNOSTIC_GPT`, `MODEL_DIAGNOSTIC_CLAUDE`, `MODEL_DIAGNOSTIC_AGGREGATE`, `HARBOR_LLMAJ`, `OFFICIAL_MODEL_TRIALS`, `TRIAL_ANALYSIS`, `DIFFICULTY_ASSESSMENT`. Detailed reviewer prompts live in `.terminus/agents/QUALITY_AGENT_PROMPTS.md` and `.terminus/agents/PROMPTS.md`; deterministic aggregation uses `.terminus/analyze_difficulty.py`.

The evaluation sequence is mandatory and ordered:

`PRE_LLMAJ -> GPT diagnostic -> Claude diagnostic -> Q8 aggregate -> Harbor LLMaJ -> official 5+5 trials -> trajectory analysis -> empirical difficulty assessment`.

Harbor LLMaJ must return a current, provenance-bound `PASS` before official model trials are dispatched. A `DISPATCHED` Harbor record is pending state, never acceptance evidence.

Final evaluation is 10 official trials total:

- GPT-5.5 / Codex ×5;
- Claude Opus 4.8 / Claude Code ×5.

Combined complete-run success sets the empirical tier:

- `<20%` frontier;
- `20%–<50%` advanced;
- `50%–<80%` core;
- `80%–<100%` base;
- `100%` reject as too easy/no signal.

A five-run model suite is diagnostic only. The 5-vs-10 question is resolved; do not create a `POLICY_CONFLICT` for it.

Solvability is separate: every individual verifier case must pass at least once somewhere across the combined 10 official trials. Any 0/10 case blocks acceptance and requires trajectory analysis/remediation before difficulty can PASS.

`TRIAL_ANALYSIS` owns trajectory/failure classification. `DIFFICULTY_ASSESSMENT` is a separate Difficulty Reviewer decision right and may PASS only when the combined success rate is below 100%, every verifier case is at least 1/10, no unresolved 0/10 case remains, trajectory analysis is complete and the declared metadata tier matches the empirical tier.

Q8 is an earlier diagnostic simulation only. `GPT_PERSPECTIVE`/`CLAUDE_PERSPECTIVE` output cannot set the tier, satisfy per-test solvability, or be represented as actual GPT-5.5/Claude Opus 4.8 evidence. Each perspective is isolated until frozen; only `MODEL_DIAGNOSTIC_AGGREGATE` may compare them.

## Review evidence provenance

Control-plane bindings: `QUALITY_INTERLOCK`, `PRE_LLMAJ`, `MODEL_DIAGNOSTIC_GPT`, `MODEL_DIAGNOSTIC_CLAUDE`, `MODEL_DIAGNOSTIC_AGGREGATE`, `HARBOR_LLMAJ`, `OFFICIAL_MODEL_TRIALS`, `TRIAL_ANALYSIS`, `DIFFICULTY_ASSESSMENT`, `FINAL_REVIEW`, `SUBMISSION_READY`. Governing lifecycle/freshness policy: `.terminus/agents/PROTOCOL.md`. Packet creation: `.terminus/new_review_packet.py`. Freshness/readiness enforcement: `.terminus/validate_review_freshness.py`. Packet/result schemas: `.terminus/agents/schemas/context_packet.schema.json` and `review_result.schema.json`.

Current semantic review evidence uses context/result schema v3.

Every review execution records:

- unique `review_id`;
- exact `task_commit`;
- role-scoped evidence hash when the role is explicitly scope-reusable (currently Q6);
- control-plane commit at invocation;
- protocol policy version;
- prompt policy version;
- role policy version;
- `role_contract_hash`;
- exact context packet path;
- exact review output path.

`.terminus/new_review_packet.py` generates the packet and refuses dirty task/governing-policy state. `.terminus/validate_review_freshness.py` validates current ready evidence and packet/result binding. Q6 scoped reuse never rewrites its original task commit; freshness is retained only when packet/result/current production-scope hashes match exactly.

Q4, Q6 and both Q8 perspective executions use the same provenance machinery. Q1/Q2/Q3/Q5/Q7 are producer/fixer evidence and cannot be promoted to semantic PASS. External Harbor/model-trial evidence additionally carries immutable external run identity and cannot be inferred from dispatch/session prose.

Historical legacy reports are retained as immutable history; they are not forced through every future schema. They also cannot support a current PASS merely because they once passed.

Current Cursor isolation is `PROCEDURAL`: excluded evidence is an operating boundary, not a filesystem ACL. Never claim stronger isolation than the runtime provides.

## Specialist roles

Role input/output interfaces for lifecycle execution are declared by the applicable stage contract; detailed decision rights/prompts remain in role-specific policy/prompt files.

### Task Architect

Decision right: is the engineering work package, contract and failure/incompleteness topology coherent, fair, realistic and technically sufficient?

### Verifier Engineer

Decision right: does the verifier cover every legitimate solver-visible requirement semantically, deterministically, independently and without easy gaming?

### Compliance Auditor

Decision right: would the current task be rejected for Edition 3 structure, environment, security, metadata, verifier or packaging rules? The same role is invoked again as Final Compliance with final artifacts/evidence.

### Difficulty Reviewer

Decision right: after the complete official 10-run evidence and trajectory analysis are current, what is the empirical tier/solvability disposition, and does it match the declared task metadata tier without any 100%-success or 0/10-case acceptance defect? Pre-trial model-family diagnostics belong to Q8, not Difficulty Reviewer.

### Human Quality Reviewer

Decision right: does final submission prose contain material synthetic cadence, benchmark boilerplate, unsupported claims or leakage?

### Instruction Writer

Producer only. Writes/revises `instruction.md` under `.terminus/agents/INSTRUCTION_POLICY.md` from the current `APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT`, solver-visible referenced contracts and human-writing calibration. It never sees hidden tests/defect IDs/oracle/prior reviews as a wording checklist, does not diagnose implementation gaps unnecessarily, and cannot approve its own draft.

### Instruction Reviewer

Cold decision right: is the instruction complete, fair, concise within the Edition 3 shape, natural as an engineering work request, free of material ambiguity/leakage/compressed-rubric construction, and correctly separated from solver-visible technical docs under `.terminus/agents/INSTRUCTION_POLICY.md`?

### Documentation Writer

Producer only. Writes README and Difficulty/Solution/Verification explanations from approved evidence.

### Engineering Documentation Reviewer

Cold decision right: are documentation/explanations supported, useful and natural rather than polished benchmark filler?

### Originality & Authenticity Reviewer

Cold decision right: is the task organically distinct rather than copied, renamed or structurally cloned from local/public references?

### Trajectory Analyst

Decision right: why did model trials succeed/fail and which layer owns remediation? It classifies every 0/10 verifier case.

### Adjudicator

Decision right: resolve material conflicts between frozen reviews using controlling evidence/rules, never majority vote. A later Q4 finding on unchanged evidence after one exhaustive repair/refreeze cycle is routed here as `LATENT_REVIEWER_OMISSION` before another normal repair loop.

### Comprehensive Reviewer

Breadth backstop. Independently walks 100% of the criterion registry and verbose checklist before specialist verdicts are shown. It reports all issues, not only the first blocker, and dispositions every available test-quality/trial-analysis flag.

### Quality specialists

Detailed missions, evidence boundaries and outputs for Q1–Q8 are authoritative in `.terminus/agents/QUALITY_AGENT_REGISTRY.md` and `.terminus/agents/QUALITY_AGENT_PROMPTS.md`. Stage-level expected inputs/outputs and routing are in `stage_contracts.json`.

### CI Orchestrator / Submission Controller

Owns routing, deterministic evidence, packet generation, staleness, circuit breakers, session state and final readiness. It cannot manufacture PASS from incomplete evidence.

The portable execution contract is `.terminus/agents/CI_ORCHESTRATOR.md`; the project-scoped callable agent is `.cursor/agents/terminus-ci-orchestrator.md`. The Orchestrator remains a controller rather than a producer or semantic reviewer and must route role work into separate chats.

Before routing an execution-relevant stage, the Orchestrator should use the applicable stage contract to identify required inputs, owner, expected output/status, evidence, validator/reviewer boundary, failure route and success transition.

When asked to wait for a queued or running GitHub Actions check, it may use bounded read-only active-chat polling under that contract. This does not create an unattended watcher; monitoring after the chat turn requires event-driven GitHub automation or an explicitly configured scheduled automation.

In Cursor, the Orchestrator uses the attached laptop's terminal and hardware for safe repository-scoped tests, linters, validators, builds, package checks and Docker verification. Local execution is preflight evidence and does not replace required current-head CI evidence.

## Routing

The table below is the human routing summary. For registered lifecycle stages, `stage_contracts.json.failure_routes` is the structured common-route surface; this policy/Protocol controls when evidence requires a different or stricter route.

| Signal | Owner |
| --- | --- |
| verifier-required behavior absent from solver spec | Q1 Spec Gap Repairer |
| solver requirement not meaningfully tested | Q2 Verifier Coverage Repairer |
| grading-relevant spec ambiguity | Q3 Spec Ambiguity Repairer |
| independent bidirectional spec/test contract on frozen candidate | Q4 Spec-Test Contract Reviewer |
| Oracle/build/runtime/application/harness failure | Q5 Oracle & Runtime Repair Specialist |
| independent production-grade code depth/reachability/padding on frozen candidate | Q6 Production Logic Auditor |
| task/task.toml/Docker/solution/test/package format | Q7 Task Format Enforcer |
| pre-model GPT/Claude strategy simulation | Q8 Model Perspective Difficulty Simulator |
| work-package/contract/failure topology | Task Architect |
| verifier coverage/quality/Oracle-NOP semantics | Verifier Engineer |
| schema/Docker/security/metadata/package acceptance review | Compliance Auditor |
| instruction creation/repair | Instruction Writer |
| instruction fairness/style/leakage | Instruction Reviewer |
| README/explanation creation | Documentation Writer |
| README/explanation quality | Engineering Documentation Reviewer |
| duplicate/template/artificial construction | Originality Reviewer |
| empirical post-trial tier/solvability | Difficulty Reviewer |
| trial failures/per-test 0-of-10 | Trajectory Analyst |
| full checklist breadth | Comprehensive Reviewer |
| material reviewer conflict or latent unchanged-scope Q4 finding | Adjudicator |
| auth/network/tool failure | Orchestrator first |

## Review order

Structured bindings:

`QUALITY_INTERLOCK -> PRE_LLMAJ -> MODEL_DIAGNOSTIC_GPT -> MODEL_DIAGNOSTIC_CLAUDE -> MODEL_DIAGNOSTIC_AGGREGATE -> HARBOR_LLMAJ -> OFFICIAL_MODEL_TRIALS -> TRIAL_ANALYSIS -> DIFFICULTY_ASSESSMENT -> FINAL_REVIEW -> SUBMISSION_READY`.

For a mature candidate:

`deterministic preflight -> Oracle/NOP -> FROZEN_CANDIDATE -> Q4 Spec-Test Contract Reviewer + Q6 Production Logic Auditor -> QUALITY_INTERLOCK_PASS -> packet-bound Stage-B specialists -> cold Comprehensive Reviewer -> omission/conflict scan -> adjudication -> Pre-LLMaJ aggregate -> Q8 GPT_PERSPECTIVE -> Q8 CLAUDE_PERSPECTIVE -> Q8 aggregate -> Harbor LLMaJ -> GPT×5 + Claude×5 -> combined 10-run evidence -> Trajectory Analyst -> Difficulty Reviewer empirical tier/solvability -> final Compliance + Human Quality -> package`

Do not show Comprehensive Reviewer specialist verdicts before its criterion walk is frozen. Do not show Q4 Q1/Q2/Q3 conclusions before Q4 freezes its own matrix. Do not show either Q8 perspective the other result before both simulations freeze.

Use `.terminus/reviewers/PRE_LLMAJ.md` panel policy 2.2 for the ordinary Pre-LLMaJ panel; the quality interlock is an additive earlier gate and Q8 is a later diagnostic simulation.

Harbor LLMaJ is a first-class mandatory `EXTERNAL_GATE` stage. The controller dispatches it only after both Q8 perspectives and the aggregate are current, records immutable run identity, projects a dispatched run to `AWAIT_EXTERNAL_GATE`, and may advance to official trials only from a current provenance-bound Harbor PASS.

## Checklist severity

Unless superseded by a current authoritative source:

- High: one failure blocks;
- ordinary Medium: multiple block; one may be `APPROVE_WITH_NOTE`;
- Low: does not block by itself;
- special trial-analysis Medium: each valid flag is independently capable of requiring revision.

Q4 uses the stricter role-specific materiality rule in `QUALITY_AGENT_PROMPTS.md`: BLOCKER/HIGH block, MEDIUM blocks when it can change solver pass/fail, externally observable correctness, safety/durability or a documented stable public interface, and LOW is advisory unless an authoritative rule makes it mandatory.

Reviewers continue after a blocker so one revision cycle receives all known issues.

## Staleness

Stage-contract `stale_on` entries provide structured dependency hints. They supplement and never weaken `.terminus/agents/PROTOCOL.md` or role-specific exact-commit/scope-hash rules.

Task changes stale the affected roles according to `PROTOCOL.md`. Governing reviewer-policy/calibration changes are tracked by role-contract hash so unrelated roles need not be rerun merely because another role changed.

Q4 stales on instruction, referenced solver-visible contract, verifier/test, or grading-semantics changes and always requires the exact current task commit. Q6 stales on `task.toml` or solver-visible `environment/` changes; tests-only, solution-only or instruction-only task changes may preserve Q6 only when its recorded production-scope hash remains identical. Q8 stales on any solver-visible task change that could alter either simulated solve or the frozen aggregate.

After an exhaustive Q4 `REVISE`, the default normal budget is one consolidated repair/refreeze cycle. If the next Q4 raises a finding whose evidence was unchanged and fully reviewable in the previous exhaustive scope, classify it `LATENT_REVIEWER_OMISSION` and route to Adjudicator instead of starting another blind repair cycle. Newly introduced or repair-touched regressions may still route normally.

Session prose cannot resurrect a stale review. Every current ready semantic row must cite an exact v3 review result whose packet/provenance validates; Q6 is the only role allowed Protocol-defined scope-preserved currentness across an unrelated task commit.

## Circuit breakers

Repeated infrastructure failures, repeated unresolved semantic findings, no-progress task changes, unresolved review conflicts, or predictably futile credential/model retries trip `BLOCKED`. Do not repeat a tripped strategy without new evidence/dependency change.

Q5 stops after two identical failures without new evidence. Persistent spec/test disagreement after two Q1/Q2/Q3 repair cycles blocks freeze and routes through the applicable contract/policy owner; Q4 is reserved for the independent post-freeze review rather than serving as a producer-side arbitration shortcut. For Q4 specifically, one consolidated normal repair/refreeze cycle follows an exhaustive `REVISE`; unchanged-scope findings after that require Adjudicator disposition before another repair.

A stage `failure_route` never overrides a tripped circuit breaker.

## Durable state

Each task has `.terminus/sessions/<task>.md`. Store current task commit, policy versions, current gate status/evidence, review IDs/paths, checklist coverage, findings/conflicts, run/artifact IDs, circuit breakers and next action. Never store secrets or raw chat transcripts.

For registered stages, durable session reconciliation should preserve references to the stage's required persisted artifacts/evidence rather than copying whole artifacts into session prose.

Quality-aware sessions should record Q1/Q2/Q3/Q7 producer status, Q4/Q6 packet/result paths, Q5 repair evidence when invoked, both Q8 perspective result paths plus the aggregate, Harbor run/result identity, official model-trial evidence, trajectory analysis and Difficulty Assessment when reached. When Q6 is retained across an unrelated task commit, record the unchanged `review_scope_hash` and the old/new task commits explicitly. Simulation rows must be labeled diagnostic, not official model evidence.

## Submission-ready definition

Control-plane binding: `SUBMISSION_READY`. Expected input/output, evidence and common failure route are in `stage_contracts.json`; final readiness enforcement remains `.terminus/validate_review_freshness.py` plus controller reconciliation under this policy/Protocol.

`SUBMISSION_READY` requires the complete mandatory gate registry, including:

- deterministic/static and verifier lint evidence;
- Oracle = 1 and NOP = 0;
- quality interlock Q4 exact-current PASS plus Q6 current PASS or Protocol-valid scope-preserved PASS for tasks advanced under this workflow;
- current Stage-B semantic reviews;
- Comprehensive Reviewer acceptable recommendation with 100% coverage;
- Pre-LLMaJ aggregate PASS;
- both Q8 perspective stages and the Q8 aggregate current (a permitted `SIMULATION_NOT_EXECUTED` remains diagnostic/non-official rather than being invented as a solve);
- Harbor LLMaJ PASS;
- all 10 model trials complete with combined success below 100%;
- every verifier case at least 1/10;
- Trial Analysis complete and all valid flags resolved;
- Difficulty Assessment PASS with declared tier matching empirical tier;
- Final Compliance current PASS;
- Final Human Quality current PASS;
- final package evidence;
- no unresolved policy conflict, adjudication, circuit breaker, stale/insufficient semantic gate or open blocking finding.

Q8 diagnostic execution is a mandatory lifecycle step before Harbor/model-backed evaluation, but its output never substitutes for Harbor or the official model gates. If a simulation cannot execute, the stage must record `SIMULATION_NOT_EXECUTED` rather than fabricating model evidence.

`.terminus/validate_review_freshness.py` enforces the provenance, scope-freshness and mandatory-gate invariants. A green workflow or a non-empty session evidence cell alone is never sufficient.
