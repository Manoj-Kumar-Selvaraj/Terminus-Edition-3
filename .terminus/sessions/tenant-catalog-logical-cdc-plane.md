# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `tenant-catalog-logical-cdc-plane`
- Controller state: `QUALITY_REPAIR`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `bf0338e23979bd7802473064fd0e02967e3de880` (stale; repair in progress)
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 02968862b6e0c36271370b97d1c75bdbeb9b9978
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; .terminus/reviewers/REVIEWER_CHECKLIST.md; CREATION_PIPELINE.md; PRODUCTION_AUTHENTICITY.md; QUALITY_AGENT_REGISTRY.md; STAGE_CONTRACTS.md
ACTIVE_VALIDATORS: validate_task_complexity.py; validate_runtime_authenticity.py; ruff; Harbor oracle/nop
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: public; environment_mode=separate; artifacts=["/app/catalog"]; golang:1.24-bookworm canonical base; bake tmux+asciinema; Python verifier-only
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Harbor oracle / NOP | STALE | pre-repair 1.0 / 0.0; must rerun after repair |
| Q4 Spec-Test | REVISE | `.terminus/reviews/tenant-catalog-logical-cdc-plane/bf0338e2/...-6b152d7cea.json` |
| Q6 Production Logic | REVISE | `.terminus/reviews/.../bf0338e2/...-711b9c2c50.json` (~2734 LOC) |
| Quality Interlock | REVISE | `.terminus/reviews/tenant-catalog-logical-cdc-plane/bf0338e2/quality-interlock.md` |

## Decisions that must survive chat changes

- Taxonomy `Software` / `Databases`.
- Profile `large_system_strict`; artifacts `["/app/catalog"]`.
- Work package is snapshot-isolation + commit-time constraints + secondary indexes + WAL-decoded logical CDC + LSN/epoch-fenced replica apply + checkpoint redo.
- Leave unrelated dirty work untouched.
- Python is verifier-only.
- Q4 blockers: document `--cdc`; assert WAL ABORT; strengthen inspect/empty-check; health after commit/decode/apply; checkpoint epoch stable.
- Q6 blocker: deepen reachable catalogctl-path runtime past 3000 LOC (not seed.sql). Added `walvalidate`, `fence`, `cdcevent` wired from engine/health/replica.

## Next action

Finish repair validation: Harbor oracle+NOP, complexity/authenticity, ruff; then refreeze and cold-rerun packet-bound Q4+Q6 on the new task commit.
