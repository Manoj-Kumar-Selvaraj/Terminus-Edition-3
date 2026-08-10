# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `DRAFT`
- Working branch: none
- Pull request: none
- Current task commit: uncommitted
- Agent-system policy: `2.3`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

Software/Languages warehouse SKU tape unpacker: COMP-3 C/D/F, REDEFINES, OCCURS DEPENDING ON. Not a payment/claims/depot ledger. No OpenAI, no GnuCOBOL, no trial network. Holdouts sealed in verifier tests. No design.json/test-map (controller asked design+test-map for tasks 1 and 2 only).

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | |
| Q2 Verifier Coverage Repair | PENDING | 16 F2P / 1 P2P |
| Q7 Task Format Enforcer | PENDING | |
| Oracle = 1 | PENDING | |
| NOP = 0 | PENDING | |
| Q4 Spec-Test Contract Reviewer | PENDING | do not self-certify |
| Q6 Production Logic Auditor | PENDING | do not self-certify |

## Current blocker

Local unpack verification + Harbor oracle/NOP. Do not self-certify Q4/Q6.

## Next action

Run fixed unpack against public sample and holdout hex, then Harbor.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Verifier checks decimals/bytes against sealed expected; oracle implements real COMP-3.
