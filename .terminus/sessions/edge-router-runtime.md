# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `edge-router-runtime`
- Controller state: `SYSTEM_ARCHITECTURE`
- Working branch: `task/edge-router-runtime`
- Pull request: `#28`
- Logical task snapshot for current creation stage: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Creation profile: `large_system_strict`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: fa2a409e86c4676bd3039df3e4e8339708454fad
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; .terminus/AGENT_SYSTEM.md; .terminus/agents/CREATION_CONTROLLER.md; .terminus/agents/CREATION_PIPELINE.md; .terminus/agents/PRODUCTION_AUTHENTICITY.md; .terminus/reviewers/REVIEWER_CHECKLIST.md; .terminus/agents/stage_contracts.json
ACTIVE_VALIDATORS: .terminus/validate_agent_system.py; .terminus/validate_stage_contracts.py; .terminus/validate_task_complexity.py; .terminus/validate_runtime_authenticity.py; .terminus/validate_review_freshness.py; .terminus/validate_quality_interlock.py; Terminus Edition 3 CI; Terminus Creator Complexity Gate; Terminus Production Authenticity Gate
CREATION_PROFILE: large_system_strict
REQUESTED_DOMAIN: production Go HTTP edge-routing and traffic-management runtime; real-time non-Python product
NETWORK/ENVIRONMENT_CONSTRAINTS: network_mode public; separate verifier; digest-pinned canonical Go runtime; no privileged Docker/capability/socket shortcuts; tmux and asciinema required in agent image
KNOWN_POLICY_CONFLICTS: none
NAMING/FRAMING_CONSTRAINT: solver-facing task material must not describe the product using the comparison prohibited by the user request
```

## Pre-workflow candidate disposition

The existing files under `edge-router-runtime/` were authored before the Edition 3 creation lifecycle was followed. They remain a discarded/pre-workflow candidate and are not accepted producer-stage evidence or inherited architecture. In particular, A2 must not treat that implementation, its oracle, or its verifier as authoritative design input.

The task uses `large_system_strict`: at least 3,000 substantive reachable solver-visible runtime/configuration LOC, 20–30 observable manifestations, at least 15 participating in meaningful causal/interdependency relationships, 25–30 organically derived F2P cases, preservation-driven P2P coverage, and production-authentic behavior without padding.

## Durable execution history

### Rule Resolution

- Invocation: `inv_66fd6ae81cde9400a2230e790c8d7e75cccb1d237c0375ca378a640e43f453f1`
- Status: `RULES_RESOLVED`
- Disposition: `ADVANCE`
- Record: `rec_db529167d9f7620f1d8a2023315a67c78acc95e4bf48f6b0ebbaaee5ad218ba3`
- Ledger event: `evt_d7aab08d8fed1baa374e21794bb633b134a57b893ff130e44161b5c67e718fd7`

### Work Package Research / A1

- Invocation: `inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8`
- Status: `CANDIDATES_READY`
- Disposition: `ADVANCE`
- Record: `rec_54b9ea6d27eea759968696bbe6eb7a68f90130603ada78ca2c1f897ba2215afb`
- Ledger event: `evt_71af0083033794cfa15f1ff7c30a6cea1d4fe80f11749aaaa24e79c76c47b862`
- Record hash: `sha256:90b93e89249a39947c46cb7da9b5295853e812d4242254af6f7eae5407eafe51`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`
- Durable record: `.terminus/executions/edge-router-runtime/inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8.result.json`
- Ledger: `.terminus/executions/edge-router-runtime/ledger.jsonl`
- Canonical A1 recorder run: GitHub Actions `32045318428`, job `95431795781`
- Exact A1 record/ledger persisted to the task branch in commit `a0ba46ae013486a1b5a8e1cab6bc5a9d38e3fc3d`

The recommended work package centers generation-safe dynamic route/upstream reconciliation: validation and compilation into immutable generations; stale/out-of-order fencing; atomic publication; endpoint identity/diffing; runtime-state preservation for unchanged endpoints; health/selection/retry/stickiness integration; draining and retirement; last-known-good preservation; checkpoint/restart recovery; and bounded observability lifecycle.

## Committed-ledger replay and A2 routing

The two-event committed ledger was replayed successfully by the repository controller in GitHub Actions run `32046069520`, job `95434167332`.

The controller resolved:

- `ledger_event_count`: `2`
- ledger head: `evt_71af0083033794cfa15f1ff7c30a6cea1d4fe80f11749aaaa24e79c76c47b862`
- lineage: `CURRENT`
- next action: `INVOKE_STAGE`
- next stage: `SYSTEM_ARCHITECTURE`
- next role: `A2_SYSTEM_ARCHITECT`
- state snapshot: `state_6ac58d198acc7a6e9ec259f6fea19f6b38801fd01b7b528f5ef4e04d59b2ea84`

## Current bounded A2 invocation

- Invocation: `inv_b9463c264c05f24c0876eb2968702df48cc551bb7bfe1c87b1a45cf9a73df239`
- Stage: `SYSTEM_ARCHITECTURE`
- Owner: `A2 System Architect / Environment Builder`
- Role ID: `A2_SYSTEM_ARCHITECT`
- Role class: `PRODUCER`
- Input task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Readiness: `READY`
- Generation evidence: GitHub Actions run `32046069520`, job `95434167332`
- State snapshot: `state_6ac58d198acc7a6e9ec259f6fea19f6b38801fd01b7b528f5ef4e04d59b2ea84`
- Success transition: `DEFECT_TOPOLOGY`

Required A2 inputs are machine-derived from the recorded A1 result:

1. `APPROVED_OPERATIONAL_REQUIREMENTS`
2. `APPROVED_WORK_PACKAGE`
3. `CREATION_RULE_CONTEXT`

No optional `DOMAIN_REFERENCE_ARCHITECTURE` or `EXISTING_TECHNICAL_CONTRACTS` were supplied, deliberately preventing the discarded starter from becoming inherited architecture.

A2 required outputs:

1. `COMPONENT_GRAPH`
2. `ENTRYPOINTS`
3. `STATE_MODEL`
4. `SOLVER_VISIBLE_DOC_PLAN`
5. `PRODUCTION_CHARACTERISTICS`
6. `SCALE_FIT`

Optional outputs: `RESOURCE_GRAPH`, `DATA_VOLUME_PLAN`, `UNRESOLVED_RISKS`.

Legal statuses: `ARCHITECTURE_READY`, `SCENARIO_TOO_SMALL`, `BLOCKED`.

### A2 evidence boundary

Allowed:
- `CONTROL_PLANE_POLICY`
- `PRIVATE_CREATION_DESIGN`
- `PUBLIC_REFERENCE`
- `SOLVER_VISIBLE_TASK`

Excluded:
- `CI_RUNTIME_EVIDENCE`
- `CURRENT_REVIEW_PACKET`
- `DURABLE_SESSION_STATE`
- `FINAL_PACKAGE_EVIDENCE`
- `MODEL_TRIAL_EVIDENCE`
- `PRIOR_REVIEW_RESULTS`
- `SOLUTION_ORACLE`
- `VERIFIER_PRIVATE`

Mandatory exact reads:
- `.terminus/agents/CREATION_PIPELINE.md`
- `.terminus/agents/CREATOR_AGENT_REGISTRY.md`
- `.terminus/agents/PRODUCTION_AUTHENTICITY.md`
- `.terminus/agents/CREATOR_PROMPTS.md`
- `.terminus/agents/A2_PHASE_PROMPTS.md`

A2 is the clean-design phase. It must not create or modify the starter environment, introduce intentional defects, inspect solution/oracle/verifier-private evidence, or author tests. Defect topology belongs only to the later A3 stage.

## Gate state

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| Rule resolution | `RULES_RESOLVED / ADVANCE` | Canonical execution record |
| Work package research | `CANDIDATES_READY / ADVANCE` | Canonical A1 record; `GENERATION_SAFE_DYNAMIC_RECONCILIATION` selected |
| System architecture | `READY / INVOCATION GENERATED` | `inv_b9463c26...`; execute in fresh A2 producer context |
| Defect topology | MISSING | Cannot begin before valid A2 record |
| Environment build | MISSING | Existing environment is discarded/pre-workflow only |
| Reference solution | MISSING | Existing solution is discarded/pre-workflow only |
| Verifier build | MISSING | Existing tests are discarded/pre-workflow only |
| Human writing research | MISSING | Not eligible yet |
| Instruction draft | MISSING | Not eligible yet |
| Q1/Q2/Q3/Q7 | MISSING | Not eligible yet |
| Assembly / complexity / authenticity | MISSING | Not eligible yet |
| Deterministic validation | MISSING | Not eligible yet |
| Freeze / Q4 / Q6 / Pre-LLMaJ / model gates | MISSING | Not eligible yet |

## Resume condition

The current ChatGPT context remains the CI Orchestrator. It must not execute A2 itself. A fresh repository-connected A2 role context must execute `inv_b9463c264c05f24c0876eb2968702df48cc551bb7bfe1c87b1a45cf9a73df239`, obey the invocation's evidence boundary and exact reads, return a schema-valid `SYSTEM_ARCHITECTURE` stage-result envelope, and stop before `DEFECT_TOPOLOGY`.

After the A2 result returns, the Orchestrator will validate and record it through the canonical execution machinery before routing A3.
