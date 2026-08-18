# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `edge-router-runtime`
- Controller state: `ENVIRONMENT_BUILD`
- Canonical lifecycle evidence branch: `main`
- Producer/controller auxiliary branch: `task/edge-router-runtime`
- Historical pull request: `#28` (merged)
- Logical task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Creation profile: `large_system_strict`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`

## Creation constraints

- Domain: production Go HTTP edge-routing and traffic-management runtime; real-time non-Python product.
- Solver-facing wording must preserve the user's neutral product framing and must not use the prohibited product comparison.
- Network/runtime: public network mode, separate verifier, digest-pinned canonical Go runtime, no privileged Docker/capability/socket shortcuts; tmux and asciinema required in the agent image.
- The original `edge-router-runtime/` implementation was pre-workflow material. ENVIRONMENT_BUILD is the first stage authorized to materialize the canonical solver starter from the clean architecture plus private defect topology.
- `large_system_strict`: at least 3,000 substantive reachable solver-visible runtime/configuration LOC, 20-30 observable defect manifestations, meaningful causal/interdependency coverage with at least 15 defect IDs, approximately 25-30 organic F2P cases downstream, and preservation-driven P2P without padding.

## Durable execution history

### RULE_RESOLUTION
- Invocation: `inv_66fd6ae81cde9400a2230e790c8d7e75cccb1d237c0375ca378a640e43f453f1`
- Status/disposition: `RULES_RESOLVED / ADVANCE`
- Record: `rec_db529167d9f7620f1d8a2023315a67c78acc95e4bf48f6b0ebbaaee5ad218ba3`
- Ledger event: `evt_d7aab08d8fed1baa374e21794bb633b134a57b893ff130e44161b5c67e718fd7`

### WORK_PACKAGE_RESEARCH / A1
- Invocation: `inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8`
- Status/disposition: `CANDIDATES_READY / ADVANCE`
- Record: `rec_54b9ea6d27eea759968696bbe6eb7a68f90130603ada78ca2c1f897ba2215afb`
- Ledger event: `evt_71af0083033794cfa15f1ff7c30a6cea1d4fe80f11749aaaa24e79c76c47b862`
- Selected work package: `GENERATION_SAFE_DYNAMIC_RECONCILIATION`

### SYSTEM_ARCHITECTURE / A2
- Invocation: `inv_b9463c264c05f24c0876eb2968702df48cc551bb7bfe1c87b1a45cf9a73df239`
- Status/disposition: `ARCHITECTURE_READY / ADVANCE`
- Record: `rec_9ebb84387605c4e80487a12f686f03bc91c4abdb86f1d58665ffcd1317c3ec11`
- Record hash: `sha256:2f54c40ee2e4934396f8d55887df05873df096e9c02cde3d96572e44d8041fa3`
- Ledger event: `evt_bdcbfe8b1d2821fe6737644a649de7c95656066d65c2fa0677fa6c46e802d2c8`

### DEFECT_TOPOLOGY / A3
- Invocation: `inv_28c1baf5125eb73cb1a52b677925c8967f6a9ceb113e42bf4c28e8f08db86f98`
- Status/disposition: `DESIGN_READY / ADVANCE`
- Record: `rec_2516bd07a48e13c6c293aa4acb99622966739d8173b4d1bfe627fa994815f2f0`
- Record hash: `sha256:fc3591b7dfefec855f064f3a5565517ca2896d71fb25a9987d62baeae38a88f7`
- Ledger event: `evt_f1c98192e311a34491b5fb6a6ac53af55c3d89eae3918ad858c244dfd73c863a`
- Canonical recorder: GitHub Actions run `32102893940`, rerun job `95606886438`.
- A3 evidence-file references were mechanically normalized to the controller's immutable `git:<commit>:<path>` + SHA-256 form; invocation, status, and topology outputs were unchanged.
- Persisted topology: `.terminus/designs/edge-router-runtime.json`.
- Topology structure: 6 root-cause clusters, 30 defects, 37 causal edges, all 30 defect IDs interrelated, cross-cluster coupling present, and partial-fix traps present.

## Four-event replay

GitHub Actions run `32103091935`, job `95607262615`, checked out `main` and replayed the committed four-event ledger successfully:

- ledger event count: `4`
- ledger head: `evt_f1c98192e311a34491b5fb6a6ac53af55c3d89eae3918ad858c244dfd73c863a`
- lineage: `CURRENT`
- controller state snapshot: `state_7722670ad5291d5ef23d4d7e3550e0d45dcb5f0608a8e3dd9ce248ebd833c7b9`
- next action: `INVOKE_STAGE`
- next stage: `ENVIRONMENT_BUILD`
- next role: `A2_ENVIRONMENT_BUILDER`

## Current bounded ENVIRONMENT_BUILD invocation

- Invocation: `inv_5bc4870797fe17e92364573d8808cb23fe7a9f65daabc328ddf0bd45a77c5b60`
- Stage: `ENVIRONMENT_BUILD`
- Owner: `A2 System Architect / Environment Builder`
- Role ID: `A2_ENVIRONMENT_BUILDER`
- Role class: `PRODUCER`
- Input task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Readiness: `READY`
- Generation evidence: GitHub Actions run `32103091935`, job `95607262615`
- State snapshot: `state_7722670ad5291d5ef23d4d7e3550e0d45dcb5f0608a8e3dd9ce248ebd833c7b9`
- Success transition: `REFERENCE_SOLUTION`

Required inputs, machine-derived from canonical records:
1. `CLEAN_SYSTEM_ARCHITECTURE`
2. `CREATION_RULE_CONTEXT`
3. `DEFECT_TOPOLOGY`
4. `SOLVER_VISIBLE_DOC_PLAN`

Optional input `DOMAIN_FIXTURE_PLAN` was not supplied.

Required successful outputs:
1. `COMPONENT_GRAPH`
2. `ENTRYPOINTS`
3. `SOLVER_VISIBLE_DOCS`
4. `INSTRUCTION_DOC_BOUNDARY`
5. `SUBSTANTIVE_LOC`
6. `PRODUCTION_CHARACTERISTICS`
7. `RUNTIME_REACHABILITY_NOTES`
8. `ENVIRONMENT_RULE_CHECKS`

Optional outputs: `RESOURCE_COUNT`, `UNRESOLVED_RISKS`.

Legal statuses: `BUILT`, `SCENARIO_TOO_SMALL`, `ARCHITECTURE_GAP`, `BLOCKED`.

Persisted artifact: `<task>/environment/`.

Declared deterministic validators:
- `.terminus/validate_task_complexity.py <task>`
- `.terminus/validate_runtime_authenticity.py <task>`
- `.terminus/validate_business_module_diversity.py <task> when applicable`

Mandatory exact reads:
- `TERMINUS_3_AI_INSTRUCTIONS.md`
- `.terminus/agents/CREATION_PIPELINE.md`
- `.terminus/agents/PRODUCTION_AUTHENTICITY.md`
- `.terminus/agents/CREATOR_PROMPTS.md`
- `.terminus/agents/A2_PHASE_PROMPTS.md`

Allowed evidence classes: `CONTROL_PLANE_POLICY`, `PRIVATE_CREATION_DESIGN`, `PUBLIC_REFERENCE`, `SOLVER_VISIBLE_TASK`.

Excluded evidence classes: `CI_RUNTIME_EVIDENCE`, `CURRENT_REVIEW_PACKET`, `DURABLE_SESSION_STATE`, `FINAL_PACKAGE_EVIDENCE`, `MODEL_TRIAL_EVIDENCE`, `PRIOR_REVIEW_RESULTS`, `SOLUTION_ORACLE`, `VERIFIER_PRIVATE`.

## Gate state

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| Rule resolution | `RULES_RESOLVED / ADVANCE` | ledger event 1 |
| Work package research | `CANDIDATES_READY / ADVANCE` | ledger event 2 |
| System architecture | `ARCHITECTURE_READY / ADVANCE` | ledger event 3 |
| Defect topology | `DESIGN_READY / ADVANCE` | ledger event 4 |
| Environment build | `READY / INVOCATION GENERATED` | `inv_5bc48707...` |
| Reference solution | MISSING | cannot begin before valid environment record |
| Verifier build | MISSING | not eligible yet |
| Human writing research / instructions / docs | MISSING | not eligible yet |
| Quality and model gates | MISSING | not eligible yet |

## Resume condition

This ChatGPT context remains the CI Orchestrator and must not execute `ENVIRONMENT_BUILD`. A fresh repository-connected `A2_ENVIRONMENT_BUILDER` context must execute exact invocation `inv_5bc4870797fe17e92364573d8808cb23fe7a9f65daabc328ddf0bd45a77c5b60`, obey its complete machine-defined inputs/evidence boundary/mandatory reads/output contract/validators/routing, materialize the canonical solver environment, return a schema-valid stage result, and stop before `REFERENCE_SOLUTION`. The Orchestrator must canonically record and replay that result before advancing.
