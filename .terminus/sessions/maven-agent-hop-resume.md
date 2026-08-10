# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `maven-agent-hop-resume`
- Controller state: `DRAFT`
- Working branch: none
- Pull request: none
- Current task commit: uncommitted
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

`maven-agent-hop-resume` is a local multi-module reactor interpreter with agent hops, shared-library pins, stash, incremental fingerprints and crash resume. Profile is `large_system` (not strict): natural LOC is far below 3k without padding.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | producer |
| Q2 Verifier Coverage Repair | PENDING | 17 F2P / 4 P2P mapped |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | |
| Creator Complexity Gate | PENDING | profile `large_system` |
| Oracle = 1 | PENDING | not yet run |
| NOP = 0 | PENDING | not yet run |
| Q4 Spec-Test Contract Reviewer | PENDING | do not self-certify |
| Q6 Production Logic Auditor | PENDING | do not self-certify |
| Quality Interlock | PENDING | |

## Current blocker

Deterministic oracle/NOP Harbor runs and independent Q4/Q6 packets. Do not self-certify Q4/Q6.

## Next action

Run local interpreter + verifier checks, then Harbor oracle/NOP.

## Decisions that must survive chat changes

- Fake Python reactor is in scope; not Jenkins controller cells, not Sonar token bind, not ansible-ci-control-plane.
- Public interface is `/app/reactor/bin/pipe` plus journal/fingerprints/archive, not READY digest / plan.json.
