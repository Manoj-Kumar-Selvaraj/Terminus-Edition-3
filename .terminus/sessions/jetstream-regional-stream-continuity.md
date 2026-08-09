# jetstream-regional-stream-continuity session

Controller: Terminus Edition 3 CI Orchestrator
Creation profile: `large_system_strict`
State: `DETERMINISTIC_VALIDATION`
Task commit before this checkpoint: `3530cfacefe7f62bed4a2713718f00ae91dd8915`

## Producer sequence

| Producer gate | Status | Evidence |
| --- | --- | --- |
| Scenario Researcher | COMPLETE | `.terminus/research/jetstream-regional-stream-continuity.md` |
| System Architect / Environment Builder | COMPLETE | task environment, three NATS domains, 12k-event deterministic state, logs/ops/docs |
| Defect Topology Designer | COMPLETE | `.terminus/designs/jetstream-regional-stream-continuity.json`: 7 clusters / 26 manifestations / cross-cluster graph |
| Reference Solution Author | COMPLETE | `jetstream-regional-stream-continuity/solution/` |
| Verifier Author | COMPLETE_PENDING_EMPIRICAL_MATRIX | 28 F2P + 6 P2P in `tests/test_continuity.py`; private test map present |
| Human Writing Researcher | COMPLETE | `.terminus/research/jetstream-regional-stream-continuity-human-writing.md` |
| Instruction Writer | COMPLETE_PENDING_COLD_REVIEW | `instruction.md` points to evidence and operational contract |
| Documentation Writer | COMPLETE_PENDING_COLD_REVIEW | `README.md` + task metadata explanations |
| Task Assembly Agent | IN_PROGRESS | CI/static/complexity/runtime/Oracle/NOP evidence not yet frozen |
| Complexity Governor | PENDING_DETERMINISTIC_EVIDENCE | Must inspect validator output and runtime reachability before FROZEN_CANDIDATE |
| Authoring Failure Diagnostician | NOT_INVOKED | Invoke only on deterministic failure |

## Scale intent

- solver-visible runtime/configuration target: >3,000 substantive LOC; measured validator result pending;
- 12,000 deterministic primary event-journal records;
- 7 root-cause clusters;
- 26 observable defect manifestations;
- 28 F2P tests;
- 6 P2P tests;
- solver-visible evidence: controller log + shift handoff + stream-state capture.

## Control-plane change in this branch

`.terminus/validate_runtime_authenticity.py` was generalized so strict non-payment tasks can declare domain-neutral scalar SQL variance checks and so COBOL depth is evaluated only when explicitly declared. Historical payment behavior remains the fallback when `variance_queries` is absent. Regression coverage is in `.terminus/tests/test_runtime_authenticity_generic.py`.

## Current evidence status

No deterministic gate is recorded PASS yet. No independent semantic reviewer has been invoked. This task is not `FROZEN_CANDIDATE`, `PRE_LLMAJ`, or `SUBMISSION_READY`.

## Next action

Open a draft PR and inspect live Actions. Run/fix, in order: control-plane tests and static checks, task complexity, runtime authenticity, environment build, Oracle, NOP, empirical per-test matrix and leakage/package checks. Route any failure to the smallest responsible producer; do not weaken a legitimate verifier case to obtain green.
