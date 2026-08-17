# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `tenant-catalog-logical-cdc-plane`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `bf0338e23979bd7802473064fd0e02967e3de880`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 458d047c28c9ac65373147bbe56f2b1b013dbc49
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; .terminus/reviewers/REVIEWER_CHECKLIST.md; CREATION_PIPELINE.md; PRODUCTION_AUTHENTICITY.md; QUALITY_AGENT_REGISTRY.md; STAGE_CONTRACTS.md
ACTIVE_VALIDATORS: validate_task_complexity.py; validate_runtime_authenticity.py; ruff; Harbor oracle/nop
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: public; environment_mode=separate; artifacts=["/app/catalog"]; golang:1.24-bookworm canonical base; bake tmux+asciinema; Python verifier-only
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Harbor oracle | PASS | reward 1.0 |
| Harbor NOP | PASS | reward 0.0; 25 F2P fail / 9 P2P pass |
| Complexity | PASS | validate_task_complexity.py |
| Runtime authenticity | PASS | validate_runtime_authenticity.py |
| Spec alignment Q1/Q2/Q3 | ALIGNED | `.terminus/contracts/tenant-catalog-logical-cdc-plane/SPEC_ALIGNMENT.md` |
| Format Q7 | FORMAT_PASS | `.terminus/contracts/tenant-catalog-logical-cdc-plane/FORMAT_GATE.md` |
| Assembly A9 | ASSEMBLED | `.terminus/contracts/tenant-catalog-logical-cdc-plane/ASSEMBLY.md` |
| Freeze | `bf0338e23979bd7802473064fd0e02967e3de880` | task tree committed |
| Q4 / Q6 | PENDING | post-freeze quality interlock only |

## Decisions that must survive chat changes

- Taxonomy `Software` / `Databases`.
- Profile `large_system_strict`; artifacts `["/app/catalog"]`.
- Work package is snapshot-isolation + commit-time constraints + secondary indexes + WAL-decoded logical CDC + LSN/epoch-fenced replica apply + checkpoint redo. Do not copy `wal-recovery-ordering` physical redo or `mvcc-lsm-compaction` LSM flush topology.
- Leave unrelated dirty work (event-time reviews/session, `.gitignore`, stray `3`, yard-gate*) untouched.
- Do not add `task.toml` explanation fields.
- Seed primary table is `row_version` at exactly 12000 deterministic records.
- Implementation language is Go for the catalog plane. Python is verifier-only (`tests/*.py`).
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless asked.

## Next action

Run packet-bound Q4 Spec-Test Contract Review and Q6 Production Logic Audit against freeze `bf0338e`. Do not treat pre-freeze producer notes as Q4/Q6 PASS.
