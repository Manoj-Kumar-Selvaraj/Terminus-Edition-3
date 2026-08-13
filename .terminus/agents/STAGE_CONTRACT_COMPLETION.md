# Terminus Stage Contract Completion

Completion policy version: `1.2`

This file closes lifecycle ambiguities that should not be inferred independently by creator/controller agents. It supplements `.terminus/agents/stage_contracts.json` without changing the authority of Edition 3 rules, `.terminus/AGENT_SYSTEM.md`, `.terminus/agents/PROTOCOL.md`, packet evidence boundaries, or role-specific exclusions.

The machine-readable companion is `.terminus/agents/stage_contract_completion.json`; its schema is `.terminus/agents/schemas/stage_contract_completion.schema.json`. A2 phase-specific executable prompts live in `.terminus/agents/A2_PHASE_PROMPTS.md`.

## A2 two-phase contract

A2 is one role with two separate invocations. The phase-specific prompt is mandatory for both A2 invocations and specializes the shared A2 obligations in `CREATOR_PROMPTS.md`.

### `SYSTEM_ARCHITECTURE` — design only

The first invocation produces the clean inherited-system architecture. It may define component/resource topology, runtime/operator entrypoints, state/persistence semantics, production characteristics, scale/reachability and the solver-visible documentation plan.

It must not consume the later private defect topology, create the broken starter, inject defects, or materialize the final task environment.

### `ENVIRONMENT_BUILD` — materialization

The second invocation runs only after `DEFECT_TOPOLOGY`. It consumes the approved clean architecture plus the approved private defect/incomplete-behavior topology and materializes the solver-visible starter/runtime/state/docs.

It may inject only tracked approved defects/incomplete behaviors. Untracked surprise defects are a producer error and must not become accidental task difficulty.

The required sequence is therefore:

`SYSTEM_ARCHITECTURE -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD`

not:

`ENVIRONMENT_BUILD -> DEFECT_TOPOLOGY`

and not one combined A2 pass.

## Freeze-state contract

`FROZEN_CANDIDATE` is a controller-owned lifecycle state with explicit entry and invalidation semantics. It is not merely a label for the newest task commit.

Entry requires current exact-commit evidence for all applicable format/packaging, complexity, runtime-authenticity and deterministic Oracle/NOP/F2P/P2P gates, with no unresolved applicable policy conflict.

The controller records the exact task commit, governing policy identity, deterministic evidence references and next gate. Any acceptance-relevant task, solution, verifier, solver-visible contract, governing policy/validator or deterministic-evidence change invalidates the freeze before further review advancement.

The only normal forward transition is:

`DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE -> QUALITY_INTERLOCK`

## Canonical creation chain

The canonical creation lifecycle is declared in `.terminus/agents/stage_contract_completion.json`. Controllers and producer prompts must not publish a contradictory ordering.

The validator must reject at least these contradictions:

- A2 described as building the broken starter before A3;
- A3 described as operating on an already defect-injected starter when the clean architecture is the approved design input;
- `ENVIRONMENT_BUILD` not depending on both `SYSTEM_ARCHITECTURE` and `DEFECT_TOPOLOGY`;
- either A2 phase not using `.terminus/agents/A2_PHASE_PROMPTS.md`;
- deterministic validation advancing directly to semantic review without an evidence-bound freeze state;
- any alternate creation chain that reverses the three design/materialization phases.

## Relation to retrieval/RAG

This completion layer is intentionally resolved before retrieval implementation. Future retrieval must know not only which stage is active and what evidence is visible, but also which lifecycle phase produced the evidence and whether the task is frozen/current. RAG or caching must never blur architecture-design evidence, private topology evidence, materialized starter evidence, or frozen acceptance evidence across these boundaries.
