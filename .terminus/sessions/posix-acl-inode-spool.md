# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `posix-acl-inode-spool`
- Controller state: `DRAFT`
- Working branch: uncommitted local tree
- Pull request: none
- Current task commit: none (do not commit)
- Agent-system policy: `2.3`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | producer draft |
| Q2 Verifier Coverage Repair | PENDING | test-map written, not empirically frozen |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | |
| Oracle = 1 | PENDING | local oracle-patched pytest 27 passed (Windows, not Harbor) |
| NOP = 0 | PENDING | local unpatched pytest 19 failed / 8 passed (reward would be 0) |
| Q4 Spec-Test Contract Reviewer | PENDING | not self-certified |
| Q6 Production Logic Auditor | PENDING | not self-certified |
| Difficulty trials | PENDING | tier in task.toml is provisional `advanced` |

## Current blocker

Fresh authoring. Deterministic local pytest against an oracle-patched tree is the next producer step. No Q4/Q6 packet exists.

## Next action

Run local oracle-patched pytest for `posix-acl-inode-spool`, then Harbor oracle/NOP when Docker is available.

## Decisions that must survive chat changes

- Userspace VFS only; no privileged mounts or pidfd/supervision crossover with linux-pidfd-service-guardian.
- large_system profile, not strict.
- Difficulty provisional until GPT-5.5 ×5 + Claude Opus 4.8 ×5.
