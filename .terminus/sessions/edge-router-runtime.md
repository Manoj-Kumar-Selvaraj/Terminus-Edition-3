# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `edge-router-runtime`
- Controller state: `WORK_PACKAGE_RESEARCH`
- Working branch: `task/edge-router-runtime`
- Pull request: `#28`
- Current task commit at reconciliation: `a2f8ddac0ef3006cde3b697c7f09056b169f0164`
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
ACTIVE_VALIDATORS: validate_agent_system.py; validate_stage_contracts.py; validate_task_complexity.py; validate_runtime_authenticity.py; validate_review_freshness.py; validate_quality_interlock.py; Terminus Edition 3 CI; Terminus Creator Complexity Gate; Terminus Production Authenticity Gate
CREATION_PROFILE: large_system_strict
REQUESTED_DOMAIN: production Go HTTP edge-routing and traffic-management runtime; real-time non-Python product
NETWORK/ENVIRONMENT_CONSTRAINTS: network_mode public; separate verifier; digest-pinned canonical Go runtime; no privileged Docker/capability/socket shortcuts; tmux and asciinema required in agent image
KNOWN_POLICY_CONFLICTS: none affecting creation-stage routing; final reviewer-checklist freshness remains to be verified at final review
NAMING/FRAMING_CONSTRAINT: solver-facing task material must not describe the product using the comparison prohibited by the user request
```

## Reconciliation of the existing PR candidate

The files currently under `edge-router-runtime/` were authored before the Edition 3 creation lifecycle was followed. They are retained only as a discarded/pre-workflow design candidate and are not evidence that any producer stage has completed.

The requested task is an Advanced operational Software/Systems task. Under the current creation policy it therefore defaults to `large_system_strict` unless the Creation Controller records a justified smaller profile. The existing candidate does not represent the required strict-scale work package: the original PR candidate had only 1,137 total added lines across task, oracle, verifier and documentation, while strict creation requires at least 3,000 substantive reachable solver-visible runtime/configuration LOC plus production-scale coupled behavior, 20–30 manifestations and organically derived 25–30 F2P cases.

No `.terminus/executions/edge-router-runtime/ledger.jsonl` exists. Historical chat statements and the pre-workflow commit are not converted into lifecycle PASS evidence.

## Current CI evidence

- `Terminus Edition 3 CI` run `32034154404`, task job `95400582147`: task preflight passed; Ruff failed on `edge-router-runtime/tests/test_outputs.py` because `os` is imported but unused. Oracle/NOP/LLMaJ did not run after that failure.
- `Terminus Production Authenticity Gate` run `32034154343`: failed in repository control-plane policy self-validation (`validate_production_policy.py`) before task-profile validation. This is not attributed to `edge-router-runtime`.
- `Terminus Creator Complexity Gate` run `32034154336`: its regression suite passed, then repository-wide profile validation failed on the existing `cobol-comp3-python-equiv` task. This is not attributed to `edge-router-runtime`; the current edge-router candidate has no strict design manifest and therefore was not evaluated by that profile validator.

## A1 research received

A fresh Scenario Researcher response was returned with `STATUS: CANDIDATES_READY` and four coherent candidates:

1. `ATOMIC_CONFIG_CONVERGENCE`
2. `FAILURE_AWARE_UPSTREAM_POOL`
3. `PROGRESSIVE_TRAFFIC_POLICY`
4. `OVERLOAD_ADMISSION_CONTROL`

The research recommends `ATOMIC_CONFIG_CONVERGENCE`. Semantically, that recommendation fits the requested domain and the `large_system_strict` policy: the work package centers one coherent control-to-data-plane convergence problem spanning validation/compilation, immutable generations, revision ordering and fencing, atomic publication/rejection, in-flight request consistency, generation drain/reclaim, durable last-known-good recovery, startup reconstruction and operator-visible revision state. The proposed scale comes from coupled responsibilities rather than unrelated feature accumulation.

The A1 output is useful creation research and should be reused as input to the bounded A1 execution rather than discarded.

### A1 provenance disposition

The returned A1 prose is **not yet lifecycle advancement evidence** under the current execution-record contract. The earlier controller handoff did not include a machine-generated stage invocation, so the response does not contain the required `invocation_id`, `output_task_commit`, structured `outputs`, and immutable `evidence_refs` defined by `.terminus/agents/schemas/stage_result.schema.json`.

Do not retroactively invent an invocation ID or fabricate a ledger PASS. The smallest repair is to compile a current `WORK_PACKAGE_RESEARCH` invocation through `.terminus/execution/controller_cli.py continue`, then have a fresh A1 context validate/re-emit the already-completed research under that exact invocation and record the resulting stage envelope through `controller_cli.py record`.

The recommendation remains `ATOMIC_CONFIG_CONVERGENCE` unless the bounded rerun finds a material contradiction.

## Gate state

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| Rule resolution | RECONCILED, not ledger-materialized | Current control-plane sources read and pinned above |
| Work package research | SEMANTIC RESULT RECEIVED / PROVENANCE REPAIR REQUIRED | A1 recommended `ATOMIC_CONFIG_CONVERGENCE`; machine invocation/result record missing |
| System architecture | MISSING | Cannot precede a valid A1 execution record |
| Defect topology | MISSING | Cannot precede clean A2 architecture |
| Environment build | MISSING | Existing task environment is pre-workflow candidate only |
| Reference solution | MISSING | Existing solution is pre-workflow candidate only |
| Verifier build | MISSING | Existing tests are pre-workflow candidate only |
| Human writing calibration | MISSING | No valid A6 calibration pair/profile for this task |
| Instruction draft | MISSING | Existing instruction is pre-workflow candidate only |
| Q1/Q2/Q3/Q7 | MISSING | Not valid before rebuilt producer artifacts exist |
| Assembly / complexity / authenticity | MISSING | Not eligible yet |
| Deterministic validation | MISSING | Oracle/NOP were never reached in current CI |
| Freeze / Q4 / Q6 / Pre-LLMaJ / model gates | MISSING | Not eligible |

## Next bounded invocation

`WORK_PACKAGE_RESEARCH` — owner `A1 Scenario Researcher` in a separate fresh role context, this time generated through the machine stage-invocation contract.

The bounded rerun should use the existing A1 research as supporting input/evidence and should not redo broad ideation unless validation reveals a material gap. It must return the exact legal stage result envelope and stop before `SYSTEM_ARCHITECTURE`.

## Current blocker

The current ChatGPT context is acting as the CI Orchestrator. `.terminus/agents/CI_ORCHESTRATOR.md` and `.terminus/agents/INVOKE.md` prohibit reusing this controller context as the routed A1 producer context. This execution surface also cannot run the repository-local controller CLI because the local runtime has no network path to clone the GitHub repository.

## Resume condition

Generate the bounded `WORK_PACKAGE_RESEARCH` invocation in a repository-local/connected execution surface, run the A1 producer under that exact invocation using the existing research as input, record the schema-valid result, then return the invocation/result/record identity to the Orchestrator. Only then route to `SYSTEM_ARCHITECTURE`.