# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `wiki-creation-counter-flap`
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
| Oracle = 1 | PENDING | Harbor not run |
| NOP = 0 | PENDING | Harbor not run |
| Q4 Spec-Test Contract Reviewer | PENDING | not self-certified |
| Q6 Production Logic Auditor | PENDING | not self-certified |
| Difficulty trials | PENDING | tier provisional `advanced` |

## Current blocker

Fresh authoring. Harbor oracle/NOP next when Docker is available.

## Next action

Harbor oracle then NOP for `wiki-creation-counter-flap`. Independent Q4/Q6 in other chats.

## Decisions that must survive chat changes

- python-application wiki-service domain: probe split + durable creation counters, not k8s cutover, not django HA.
- Two replicas 8001/8002, sqlite flap via wikictl.
- Difficulty provisional until GPT-5.5 ×5 + Claude Opus 4.8 ×5.
