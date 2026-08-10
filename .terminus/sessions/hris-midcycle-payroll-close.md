# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `hris-midcycle-payroll-close`
- Controller state: `DRAFT`
- Working branch: none
- Pull request: none
- Current task commit: uncommitted
- Agent-system policy: `2.3`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

Operations/Compliance mid-cycle payroll close. Profile `large_system` (not strict) with a 12,000-employee deterministic seed and production.json variance queries. Starter ignores in-period transfers, always applies non-exempt OT, appends on double close, and counts post-cutoff punches.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | |
| Q2 Verifier Coverage Repair | PENDING | 17 F2P / 3 P2P mapped |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | |
| Production Authenticity Gate | PENDING | schema+seed + production.json |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| Q4 Spec-Test Contract Reviewer | PENDING | do not self-certify |
| Q6 Production Logic Auditor | PENDING | do not self-certify |

## Current blocker

Deterministic oracle/NOP and independent Q4/Q6. Do not self-certify Q4/Q6.

## Next action

Validate seed+authenticity locally, then Harbor oracle/NOP.

## Decisions that must survive chat changes

- Build empty HrSystems payroll/leave/attendance logic; local fake IdP file only.
- Public interface is `/app/hris/bin/hrctl` plus register/retro/dump JSON.
