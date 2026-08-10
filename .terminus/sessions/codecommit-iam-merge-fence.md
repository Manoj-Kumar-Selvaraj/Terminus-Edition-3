# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `codecommit-iam-merge-fence`
- Controller state: `DRAFT`
- Working branch: uncommitted local tree
- Pull request: none
- Current task commit: none (do not commit)
- Agent-system policy: `2.3`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | producer draft |
| Q2 Verifier Coverage Repair | PENDING | test-map written |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | |
| Oracle = 1 | PENDING | local oracle-patched pytest 24 passed (Windows + git, not Harbor) |
| NOP = 0 | PENDING | local unpatched pytest 16 failed / 8 passed (reward would be 0) |
| Q4 Spec-Test Contract Reviewer | PENDING | not self-certified |
| Q6 Production Logic Auditor | PENDING | not self-certified |
| Difficulty trials | PENDING | tier in task.toml is provisional `advanced` |

## Current blocker

Fresh authoring. Distinct from ansible-ci-control-plane (no runner queue) and terraform-http-backend. No Q4/Q6 packet exists.

## Next action

Run local oracle-patched pytest for `codecommit-iam-merge-fence` (requires git). Harbor oracle/NOP when Docker is available.

## Decisions that must survive chat changes

- Security/AppSec taxonomy. Instruction voice is platform security, not an ops drop-box note.
- large_system profile, not strict.
- Difficulty provisional until both model families are measured.
