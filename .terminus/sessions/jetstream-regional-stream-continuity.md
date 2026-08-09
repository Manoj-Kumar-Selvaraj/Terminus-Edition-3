# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-regional-stream-continuity`
- Pull request: `#10` (draft creation/validation PR)
- Current task commit: `1df881cd83a8713593fbf6f530adec0469184bed`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Production-authenticity policy: `1.1`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Current task profile

`jetstream-regional-stream-continuity` models a three-domain NATS JetStream regional telemetry continuity incident. Two edge domains accept telemetry into durable journals/origin streams while a hub sources both origins, maintains an application archive index, drives required durable consumers and controls replay/retention. The inherited reconnect state intentionally disagrees across edge journal membership, hub archive membership, application effects/checkpoints, JetStream acknowledgement evidence, replay plans and cleanup watermarks.

The strict design contains seven materially different root-cause clusters and 26 observable manifestations with cross-cluster causal edges. The verifier map contains 28 F2P behavioral cases and six P2P preservation cases. The deterministic state contains 12,000 primary telemetry events plus device, generation, archive, effect, checkpoint, replay and retention state. Solver-visible incident evidence is the archived controller log, shift handoff and captured stream-state artifact.

## Producer sequence

| Producer gate | Status | Evidence |
| --- | --- | --- |
| Scenario Researcher | COMPLETE | `.terminus/research/jetstream-regional-stream-continuity.md` |
| System Architect / Environment Builder | COMPLETE | task environment, three NATS domains, deterministic 12k-event state, logs/ops/docs |
| Defect Topology Designer | COMPLETE | `.terminus/designs/jetstream-regional-stream-continuity.json`: 7 clusters / 26 manifestations / cross-cluster graph |
| Reference Solution Author | COMPLETE | `jetstream-regional-stream-continuity/solution/` |
| Verifier Author | COMPLETE_PENDING_EMPIRICAL_MATRIX | 28 F2P + 6 P2P in `tests/test_continuity.py`; private test map present |
| Human Writing Researcher | COMPLETE | `.terminus/research/jetstream-regional-stream-continuity-human-writing.md` |
| Instruction Writer | COMPLETE_PENDING_COLD_REVIEW | `instruction.md` points to evidence and operational contract |
| Documentation Writer | COMPLETE_PENDING_COLD_REVIEW | `README.md` + task metadata explanations |
| Task Assembly Agent | IN_PROGRESS | fresh-head preflight/Ruff/environment/Oracle/NOP evidence pending |
| Complexity Governor | PENDING_FRESH_HEAD_EVIDENCE | earlier strict complexity workflow passed at `445c551e`; current task commit moved when verifier packaging was completed |
| Authoring Failure Diagnostician | ACTIVE_AS_NEEDED | control-plane/session/preflight defects are routed here rather than weakening task behavior |

## Deterministic gate registry

| Gate | Status | Evidence / note |
| --- | --- | --- |
| Creator Complexity Gate | STALE_PASS | PR #10 run `31298650580`, job `93207750567` passed on earlier task head `445c551e`; rerun required for current task commit |
| Production Authenticity Gate | STALE_PASS | PR #10 run `31298650550` passed on earlier task head `445c551e`; rerun required for current task commit |
| Agent System / control-plane regressions | PENDING | initial run `31298650633`, job `93207750777` failed; generic authenticity fixture/session format were corrected and fresh run is required |
| Preflight/static | PENDING | `tests/Dockerfile` was added after workflow contract inspection |
| Ruff verifier | PENDING | fresh main validation run pending |
| Environment build | PENDING | main validation run pending |
| Oracle = 1 | PENDING | main validation run pending |
| NOP = 0 | PENDING | main validation run pending |
| F2P empirical matrix | PENDING | must prove every one of 28 F2P starter-fail / Oracle-pass |
| P2P empirical matrix | PENDING | must prove intended six preservation cases |
| Leakage/package checks | PENDING | after deterministic runtime validation |
| FROZEN_CANDIDATE | NOT_REACHED | creator cannot advance until all deterministic freeze conditions have current evidence |

## Scale and authenticity intent

- solver-visible runtime/configuration requirement: `>3000` substantive reachable LOC; fresh strict complexity result pending;
- 12,000 deterministic primary `event_journal` records with domain-specific variance across regions, devices, sites, event types, payload sizes, priorities and publish states;
- 7 root-cause clusters;
- 26 observable defect manifestations;
- 28 F2P tests;
- 6 P2P tests;
- incident evidence: controller log + shift handoff + stream-state capture;
- major logic lives in the domain model, transactional store, continuity/recovery engine, JetStream runtime integration and operator CLI rather than generated/dead padding.

## Control-plane change in this branch

`.terminus/validate_runtime_authenticity.py` was generalized so strict non-payment tasks can declare domain-neutral scalar SQL variance checks. COBOL depth is evaluated only when explicitly declared. Historical payment behavior remains the fallback when no generic variance profile is declared. Regression coverage is in `.terminus/tests/test_runtime_authenticity_generic.py`; the test dataset uses a deterministic digit cross-join rather than recursive row generation.

## Semantic review status

No independent semantic reviewer has been invoked and no producer result is represented as acceptance evidence. Task Architect, Verifier Engineer, Originality, Difficulty Design, Compliance, Instruction, Documentation and Comprehensive Reviewer remain pending until a deterministic `FROZEN_CANDIDATE` exists and fresh packet-bound reviews are generated.

## Next action

Use live PR #10 Actions on the current task commit. Resume from the first failed deterministic gate: control-plane regressions -> preflight/Ruff -> environment build -> Oracle -> NOP -> empirical F2P/P2P matrix -> leakage/package checks. If a deterministic failure occurs, route it to the smallest responsible producer and preserve the verifier requirement unless the contract itself is proven wrong.
