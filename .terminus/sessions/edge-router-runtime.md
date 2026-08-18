# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `edge-router-runtime`
- Controller state: `DEFECT_TOPOLOGY`
- Canonical lifecycle evidence branch: `main`
- Producer/controller auxiliary branch: `task/edge-router-runtime`
- Pull request: `#28` (merged)
- Logical task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Creation profile: `large_system_strict`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`

## Creation constraints

- Domain: production Go HTTP edge-routing and traffic-management runtime; real-time non-Python product.
- Network/runtime: public network mode, separate verifier, digest-pinned canonical Go runtime, no privileged Docker/capability/socket shortcuts; tmux and asciinema required in the agent image.
- Solver-facing wording must preserve the user's neutral product framing and must not describe the product using the prohibited comparison.
- The original files under `edge-router-runtime/` were authored before the Edition-3 lifecycle and remain discarded pre-workflow material until replaced by the authorized materialization stages.

## Strict-profile target

`large_system_strict` requires production-authentic breadth: at least 3,000 substantive reachable solver-visible runtime/configuration LOC, 20–30 observable defect manifestations, meaningful interdependency with at least 15 defect IDs participating in causal edges, approximately 25–30 organic nonduplicative F2P cases, and preservation-driven P2P coverage without padding.

## Durable execution history

### Rule Resolution

- Invocation: `inv_66fd6ae81cde9400a2230e790c8d7e75cccb1d237c0375ca378a640e43f453f1`
- Status/disposition: `RULES_RESOLVED / ADVANCE`
- Record: `rec_db529167d9f7620f1d8a2023315a67c78acc95e4bf48f6b0ebbaaee5ad218ba3`
- Ledger event: `evt_d7aab08d8fed1baa374e21794bb633b134a57b893ff130e44161b5c67e718fd7`

### Work Package Research / A1

- Invocation: `inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8`
- Status/disposition: `CANDIDATES_READY / ADVANCE`
- Record: `rec_54b9ea6d27eea759968696bbe6eb7a68f90130603ada78ca2c1f897ba2215afb`
- Ledger event: `evt_71af0083033794cfa15f1ff7c30a6cea1d4fe80f11749aaaa24e79c76c47b862`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`

### System Architecture / A2

- Invocation: `inv_b9463c264c05f24c0876eb2968702df48cc551bb7bfe1c87b1a45cf9a73df239`
- Status/disposition: `ARCHITECTURE_READY / ADVANCE`
- Record: `rec_9ebb84387605c4e80487a12f686f03bc91c4abdb86f1d58665ffcd1317c3ec11`
- Record hash: `sha256:2f54c40ee2e4934396f8d55887df05873df096e9c02cde3d96572e44d8041fa3`
- Ledger event: `evt_bdcbfe8b1d2821fe6737644a649de7c95656066d65c2fa0677fa6c46e802d2c8`
- Canonical successful recorder run: GitHub Actions `32095049963`, job `95584677065`.
- Exact record and three-event ledger were persisted to `main` by the canonical recorder and subsequently replayed successfully.

A2 clean architecture establishes immutable serving snapshots, single-writer reconciliation, atomic publication, stable route/pool/endpoint identities, endpoint membership incarnations and draining, reusable health/selection/affinity runtime state, checkpoint durability/recovery, bounded observability lifecycle, public data plane, and separate admin/operator surfaces. A2 contains clean design only; intentional defects belong to A3.

## Committed-ledger replay after A2

GitHub Actions run `32095373856`, job `95585603419`, checked out `main` and replayed the committed three-event ledger successfully:

- event count: `3`
- ledger head: `evt_bdcbfe8b1d2821fe6737644a649de7c95656066d65c2fa0677fa6c46e802d2c8`
- lineage: `CURRENT`
- controller state snapshot: `state_bc6de7d58a6fade2b862aa4d162066e7015733dc10d4aa4878ffee446a9e64d0`
- next action: `INVOKE_STAGE`
- next stage: `DEFECT_TOPOLOGY`
- next role: `A3_DEFECT_TOPOLOGY_DESIGNER`

## Current bounded A3 invocation

- Invocation: `inv_28c1baf5125eb73cb1a52b677925c8967f6a9ceb113e42bf4c28e8f08db86f98`
- Stage: `DEFECT_TOPOLOGY`
- Owner: `A3 Defect Topology Designer`
- Role ID: `A3_DEFECT_TOPOLOGY_DESIGNER`
- Role class: `PRODUCER`
- Input task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Readiness: `READY`
- Generation evidence: GitHub Actions run `32095373856`, job `95585603419`
- State snapshot: `state_bc6de7d58a6fade2b862aa4d162066e7015733dc10d4aa4878ffee446a9e64d0`
- Success transition: `ENVIRONMENT_BUILD`

Required A3 inputs are machine-derived from the committed A1/A2 records:

1. `APPROVED_OPERATIONAL_REQUIREMENTS`
2. `APPROVED_WORK_PACKAGE`
3. `CLEAN_SYSTEM_ARCHITECTURE`
4. `CREATION_PROFILE`

Optional input: `DOMAIN_FAILURE_REFERENCES` (not supplied).

Required successful A3 outputs:

1. `profile`
2. `root_cause_clusters`
3. `defects`
4. `causal_edges`
5. `behavioral_surfaces`
6. `organic_f2p_surface_assessment`

Legal statuses: `DESIGN_READY`, `SCENARIO_TOO_SMALL`, `BLOCKED`.

A3 evidence requirements: root-cause clusters, causal/interdependency edges, partial-fix traps, and behavioral surfaces. Deterministic validator: `.terminus/validate_task_complexity.py <task>`. Persisted artifact contract: `.terminus/designs/<task>.json`.

### A3 evidence boundary

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
- `.terminus/agents/CREATOR_PROMPTS.md`

Failure routing:
- `ARCHITECTURE_GAP` -> Creation Controller / SYSTEM_ARCHITECTURE
- `HIDDEN_KNOWLEDGE` -> A3 must expose a legitimate solver-visible contract or remove the defect
- `SCENARIO_TOO_SMALL` -> Creation Controller / WORK_PACKAGE_RESEARCH

## Gate state

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| Rule resolution | `RULES_RESOLVED / ADVANCE` | Canonical record + ledger event 1 |
| Work package research | `CANDIDATES_READY / ADVANCE` | Canonical A1 record + ledger event 2 |
| System architecture | `ARCHITECTURE_READY / ADVANCE` | Canonical A2 record + ledger event 3 |
| Defect topology | `READY / INVOCATION GENERATED` | `inv_28c1baf5...` |
| Environment build | MISSING | Cannot begin before valid A3 record |
| Reference solution | MISSING | Not eligible yet |
| Verifier build | MISSING | Not eligible yet |
| Human writing research | MISSING | Not eligible yet |
| Instruction draft | MISSING | Not eligible yet |
| Q1/Q2/Q3/Q7 | MISSING | Not eligible yet |
| Assembly / complexity / authenticity | MISSING | Not eligible yet |
| Deterministic validation | MISSING | Not eligible yet |
| Freeze / Q4 / Q6 / Pre-LLMaJ / model gates | MISSING | Not eligible yet |

## Resume condition

This ChatGPT context remains the CI Orchestrator and must not execute A3 itself. A fresh repository-connected `A3_DEFECT_TOPOLOGY_DESIGNER` context must execute exact invocation `inv_28c1baf5125eb73cb1a52b677925c8967f6a9ceb113e42bf4c28e8f08db86f98`, obey its evidence boundary and mandatory reads, return a schema-valid `DEFECT_TOPOLOGY` stage-result envelope, and stop before `ENVIRONMENT_BUILD`. The Orchestrator must canonically record/replay A3 before routing environment materialization.
