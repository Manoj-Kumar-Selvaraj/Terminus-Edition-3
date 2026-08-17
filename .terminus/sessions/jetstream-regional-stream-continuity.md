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
| Complexity | PASS | `validate_task_complexity.py` LOC 5658, 27 F2P, 8 P2P, 24 defects |
| Runtime authenticity | PASS | `validate_runtime_authenticity.py` 12000 journal rows |
| Ruff | PASS | `tests/test_outputs.py` clean |
| Harbor Oracle | PASS | `jobs/2026-08-17__13-51-51` reward **1.0** (35/35); rerun `jobs/2026-08-17__14-06-34` reward **1.0** |
| Harbor NOP | PASS | `jobs/2026-08-17__14-03-47` reward **0.0** |
| Freeze | PENDING | this commit |
| Q4 Spec-Test Contract Reviewer | PENDING | packet-bound cold review after freeze |
| Q6 Production Logic Auditor | PENDING | packet-bound cold review after freeze |
| Quality Interlock | PENDING | Q4 exact + Q6 exact/scope-preserved |

## Rebuild notes

- Reused the authentic 12k journal, NATS lab, store/model/policy/runtime substrate.
- Split starter defects into leaf modules; oracle copies `solution/fixed/*` rather than one engine swap.
- Tests drive CLI / SQLite / live JetStream and do not import ContinuityEngine.
- Removed invalid `reconnect` keys from east/west leafnode remotes (nats-server 2.14.3).
- Removed unused `starter_cli.py` leftover.

## Current blocker

None for freeze. Next: generate Q4/Q6 packets on the freeze SHA and run cold inherit/auto reviews.

## Next action

Commit freeze, then invoke Q4 Spec-Test Contract Reviewer and Q6 Production Logic Auditor independently.
