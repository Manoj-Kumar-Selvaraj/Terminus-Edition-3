# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-regional-stream-continuity`
- Pull request: `#10` (draft creation/validation PR)
- Current task commit: `795fe7f6f1f44c8f54d0c2b8d8d7a00362db1a75`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
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
| Task Assembly Agent | IN_PROGRESS | fresh-head environment/Oracle/NOP evidence pending |
| Complexity Governor | PENDING_FRESH_HEAD_EVIDENCE | strict gate has repeatedly passed, but exact task commit moved for verifier artifact packaging |
| Authoring Failure Diagnostician | ACTIVE_AS_NEEDED | deterministic failures are routed to the responsible layer without weakening legitimate verifier behavior |

## Deterministic gate registry

| Gate | Status | Evidence / note |
| --- | --- | --- |
| Creator Complexity Gate | STALE_PASS | latest nearby strict complexity run passed before verifier artifact packaging changed the task commit; rerun required by provenance |
| Production Authenticity Gate | STALE_PASS | latest nearby production-authenticity run passed before verifier artifact packaging changed the task commit; rerun required by provenance |
| Agent System / control-plane regressions | STALE_PASS | latest nearby Agent-System run passed; exact branch head rerun required |
| Preflight/static | STALE_PASS | main validation passed preflight on prior task commit; artifact boundary changed afterward |
| Ruff verifier | STALE_PASS | Ruff passed on prior task commit after the F401-only verifier config fix; rerun required |
| Environment build | STALE_PASS | Oracle run on prior task commit built environment and verifier images successfully |
| Oracle = 1 | FIX_APPLIED_PENDING_RERUN | run `31298999790`, job `93208674425` reached verifier but reward `0` because separate verifier received only `/app/continuity/out`; artifacts now export `/app/continuity` and verifier workdir is prepared to receive it |
| NOP = 0 | PENDING | prior run was skipped after Oracle failure; fresh run pending |
| F2P empirical matrix | PENDING | must prove every one of 28 F2P starter-fail / Oracle-pass |
| P2P empirical matrix | PENDING | must prove intended six preservation cases |
| Leakage/package checks | PENDING | after deterministic runtime validation |
| FROZEN_CANDIDATE | NOT_REACHED | creator cannot advance until all deterministic freeze conditions have current evidence |

## Scale and authenticity intent

- solver-visible runtime/configuration requirement: `>3000` substantive reachable LOC; strict complexity gate has passed on prior nearby heads and must be fresh on the exact current commit;
- 12,000 deterministic primary `event_journal` records with domain-specific variance across regions, devices, sites, event types, payload sizes, priorities and publish states;
- 7 root-cause clusters;
- 26 observable defect manifestations;
- 28 F2P tests;
- 6 P2P tests;
- incident evidence: controller log + shift handoff + stream-state capture;
- major logic lives in the domain model, transactional store, continuity/recovery engine, JetStream runtime integration and operator CLI rather than generated/dead padding.

## Control-plane maintenance performed during creation

`.terminus/validate_runtime_authenticity.py` was generalized so strict non-payment tasks can declare domain-neutral scalar SQL variance checks. COBOL depth is evaluated only when explicitly declared. Historical payment behavior remains the fallback when no generic variance profile is declared. Regression coverage is in `.terminus/tests/test_runtime_authenticity_generic.py`; the test dataset uses a deterministic digit cross-join rather than recursive row generation.

The repository also contained a genuinely stale `payment-eod-control-chain` session after task commit `ee7df06085a5...` changed solver-visible files. That unrelated session was corrected by preserving its historical evidence as `STALE` and returning its controller state to deterministic validation; the payment task itself was not changed.

## Semantic review status

No independent semantic reviewer has been invoked and no producer result is represented as acceptance evidence. Task Architect, Verifier Engineer, Originality, Difficulty Design, Compliance, Instruction, Documentation and Comprehensive Reviewer remain pending until a deterministic `FROZEN_CANDIDATE` exists and fresh packet-bound reviews are generated.

## Next action

Use live PR #10 Actions on the exact current task commit. Resume from environment build -> Oracle -> NOP -> empirical F2P/P2P matrix -> leakage/package checks. If a deterministic failure occurs, route it to the smallest responsible producer and preserve the verifier requirement unless the contract itself is proven wrong.
