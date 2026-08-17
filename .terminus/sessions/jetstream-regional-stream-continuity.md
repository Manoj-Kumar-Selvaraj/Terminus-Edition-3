# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: local
- Pull request: none
- Current task commit: pending this freeze commit
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: recorded at freeze HEAD
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; AGENT_SYSTEM.md; CREATION_PIPELINE.md; PRODUCTION_AUTHENTICITY.md
ACTIVE_VALIDATORS: validate_task_complexity.py; validate_runtime_authenticity.py; ruff; Harbor oracle/nop
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: public; separate verifier; digest-pinned debian + nats-server 2.14.3
KNOWN_POLICY_CONFLICTS: none
SUBAGENT_MODEL_POLICY: inherit/auto only
```

## Selected work package

Complete the inherited east/west/hub JetStream continuity control plane so reconnect recovery is identity-safe: stable Nats-Msg-Id, origin-generation fencing, source-only hub archive, idempotent consumer effects, identity reconciliation, overlap-safe replay leases, and retention gated on archive/consumer/replay watermarks.

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Complexity | PASS | `validate_task_complexity.py` LOC 5633, 27 F2P, 8 P2P, 24 defects |
| Runtime authenticity | PASS | `validate_runtime_authenticity.py` 12000 journal rows |
| Ruff | PASS | `tests/test_outputs.py` clean |
| Harbor Oracle | PASS | `jobs/2026-08-17__15-25-58` reward **1.0** (35/35) after Q4 repair |
| Harbor NOP | PASS | `jobs/2026-08-17__15-36-49` reward **0.0** |
| Freeze | PENDING | this commit |
| Q4 Spec-Test | PENDING | cold rerun on this freeze; prior `55267874` was REVISE |
| Q6 Production Logic | PENDING | rerun; contract.md changed so prior scope hash is stale |
| Quality Interlock | PENDING | Q4 exact + Q6 exact/scope-preserved |

## Historical reviews on 55267874

- Q4 REVISE: `.terminus/reviews/jetstream-regional-stream-continuity/55267874/jetstream-regional-stream-continuity-55267874-spec-test-contract-4bb21b31e6.json` (Q4-001..007)
- Q6 PASS: `.terminus/reviews/jetstream-regional-stream-continuity/55267874/jetstream-regional-stream-continuity-55267874-production-logic-e9666e0d18.json`

## Q4 repair included in this freeze

Closed blocking Q4-001..007 via verifier/contract edits. Prior Q4/Q6 packets remain historical.

## Next action

Generate Q4/Q6 packets on the freeze SHA and run cold inherit/auto reviews.
