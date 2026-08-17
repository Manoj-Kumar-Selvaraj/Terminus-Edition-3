# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `edge-router-runtime`
- Controller state: `WORK_PACKAGE_RESEARCH`
- Working branch: `task/edge-router-runtime`
- Pull request: `#28`
- Logical task snapshot for current creation stage: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Agent-system policy: `2.5`
- Creator pipeline policy: `1.1`
- Creator registry policy: `1.0`
- Quality-agent policy: `1.1`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

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

## Reconciliation of the pre-workflow task candidate

The existing files under `edge-router-runtime/` were authored before the Edition 3 creation lifecycle was followed. They remain a discarded/pre-workflow candidate and are not accepted producer-stage evidence.

This Advanced operational Software/Systems task uses `large_system_strict`. The original candidate does not meet the strict work-package shape: strict creation requires at least 3,000 substantive reachable solver-visible runtime/configuration LOC, 20–30 observable manifestations, at least 15 participating in meaningful causal/interdependency relationships, and 25–30 organically derived F2P cases, plus preservation-driven P2P coverage and production-authentic behavior.

## Rule Resolution — durable execution

`RULE_RESOLUTION` is now ledger-materialized through the repository's canonical invocation/result/record machinery.

- Invocation: `inv_66fd6ae81cde9400a2230e790c8d7e75cccb1d237c0375ca378a640e43f453f1`
- Status: `RULES_RESOLVED`
- Disposition: `ADVANCE`
- Record: `rec_db529167d9f7620f1d8a2023315a67c78acc95e4bf48f6b0ebbaaee5ad218ba3`
- Ledger event: `evt_d7aab08d8fed1baa374e21794bb633b134a57b893ff130e44161b5c67e718fd7`
- Input/output task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane evidence: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Durable record: `.terminus/executions/edge-router-runtime/inv_66fd6ae81cde9400a2230e790c8d7e75cccb1d237c0375ca378a640e43f453f1.result.json`
- Ledger: `.terminus/executions/edge-router-runtime/ledger.jsonl`
- Committed-ledger replay: GitHub Actions run `32040419728`, job `95418624275`, PASS; controller resolved the next action as `WORK_PACKAGE_RESEARCH` owned by `A1_SCENARIO_RESEARCHER`.

Temporary GitHub Actions workflows used only to execute/replay the controller in a full Git checkout were removed after validation; they are not part of the task package.

## A1 research received before bounded invocation

A fresh Scenario Researcher response previously returned four coherent work-package candidates:

1. `ATOMIC_CONFIG_CONVERGENCE`
2. `FAILURE_AWARE_UPSTREAM_POOL`
3. `PROGRESSIVE_TRAFFIC_POLICY`
4. `OVERLOAD_ADMISSION_CONTROL`

That response recommended `ATOMIC_CONFIG_CONVERGENCE`. Semantically, it is a strong `large_system_strict` direction because validation/compilation, immutable generations, revision ordering and fencing, atomic publication/rejection, request-generation consistency, generation drain/reclaim, durable last-known-good recovery, startup reconstruction, and revision observability form one coupled production responsibility rather than unrelated feature accumulation.

The earlier response remains useful research context, but it is not itself lifecycle advancement evidence because it predates the canonical A1 invocation. It must not be retroactively wrapped or treated as a recorded PASS.

## Current bounded A1 invocation

The canonical controller generated a READY `WORK_PACKAGE_RESEARCH` invocation:

- Invocation: `inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8`
- Stage: `WORK_PACKAGE_RESEARCH`
- Owner: `A1 Scenario Researcher`
- Role ID: `A1_SCENARIO_RESEARCHER`
- Input task snapshot: `6c91b9aca662fa192c144d55c8aee0e693adcc0d`
- Control-plane commit: `fa2a409e86c4676bd3039df3e4e8339708454fad`
- Readiness: `READY`
- Required outputs: `CANDIDATES`, `RECOMMENDATION`, `WHY_THIS_ONE`
- Legal success status: `CANDIDATES_READY`
- Success transition: `SYSTEM_ARCHITECTURE`
- Invocation generation evidence: GitHub Actions run `32040322187`, job `95418358086`
- Controller state snapshot: `state_7d6fc5390c4c642d5b0f906becc4cabcbcdfea4ffdc84ea8d9e23d501138c47e`

A1 evidence boundary from the machine packet:

- allowed: `CONTROL_PLANE_POLICY`, `PUBLIC_REFERENCE`, `SOLVER_VISIBLE_TASK`
- excluded: `CI_RUNTIME_EVIDENCE`, `CURRENT_REVIEW_PACKET`, `DURABLE_SESSION_STATE`, `FINAL_PACKAGE_EVIDENCE`, `MODEL_TRIAL_EVIDENCE`, `PRIOR_REVIEW_RESULTS`, `PRIVATE_CREATION_DESIGN`, `SOLUTION_ORACLE`, `VERIFIER_PRIVATE`
- mandatory exact reads: `.terminus/agents/CREATION_PIPELINE.md`, `.terminus/agents/CREATOR_AGENT_REGISTRY.md`, `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/agents/CREATOR_PROMPTS.md`

## Gate state

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| Rule resolution | `RULES_RESOLVED / ADVANCE` | Canonical record + hash-chained ledger; replay PASS |
| Work package research | `READY / INVOCATION GENERATED` | `inv_79d4551c...`; must execute in fresh A1 producer context |
| System architecture | MISSING | Cannot start before a valid A1 execution record |
| Defect topology | MISSING | Cannot precede clean A2 architecture |
| Environment build | MISSING | Existing environment is pre-workflow candidate only |
| Reference solution | MISSING | Existing solution is pre-workflow candidate only |
| Verifier build | MISSING | Existing tests are pre-workflow candidate only |
| Human writing calibration | MISSING | No valid A6 calibration/profile yet |
| Instruction draft | MISSING | Existing instruction is pre-workflow candidate only |
| Q1/Q2/Q3/Q7 | MISSING | Not eligible yet |
| Assembly / complexity / authenticity | MISSING | Not eligible yet |
| Deterministic validation | MISSING | Not eligible yet |
| Freeze / Q4 / Q6 / Pre-LLMaJ / model gates | MISSING | Not eligible yet |

## Current blocker and resume condition

The current ChatGPT context is the CI Orchestrator. `.terminus/agents/CI_ORCHESTRATOR.md` and `.terminus/agents/INVOKE.md` prohibit reusing this controller context as the A1 producer. A fresh role-specific repository-connected chat must execute `inv_79d4551ca8b96875e1f37dc7cea565949e1ade639e32fa1b5de68d5a081bf0d8` under its machine-defined evidence boundary and return a schema-valid stage result envelope for task snapshot `6c91b9aca662fa192c144d55c8aee0e693adcc0d`.

After the A1 result is returned, the Orchestrator will validate and record it through the same canonical execution machinery. Only a valid A1 `CANDIDATES_READY / ADVANCE` record may route the task to `SYSTEM_ARCHITECTURE`.
