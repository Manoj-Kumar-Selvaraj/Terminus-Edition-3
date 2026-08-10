# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `DRAFT`
- Working branch: `task/cobol-comp3-python-equiv`
- Pull request: pending (branch pushed; `gh` auth needed for PR create)
- Current task commit: `32de80a57ddbc38acd33d36cac598c69abe99da8`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

Software/Languages warehouse SKU tape unpacker: COMP-3 C/D/F, REDEFINES, OCCURS DEPENDING ON. Not a payment/claims/depot ledger. No OpenAI, no GnuCOBOL, no trial network. Holdouts and invalid-sign/ODO fixtures sealed in verifier tests.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PENDING | producer rework added incident paths + invalid-record contract coverage |
| Q2 Verifier Coverage Repair | PENDING | F2P includes holdouts + invalid sign/ODO + rerun |
| Q3 Spec Ambiguity Repair | PENDING | |
| Q7 Task Format Enforcer | PENDING | |
| Oracle = 1 | PASS | Harbor `/tmp/e3-cobol-equiv-jobs/2026-08-11__00-13-19` trial `cobol-comp3-python-equiv__63YHogS` reward 1 |
| NOP = 0 | PASS | Harbor `/tmp/e3-cobol-equiv-jobs/2026-08-11__00-14-42` trial `cobol-comp3-python-equiv__ovBoSbo` reward 0 |
| Q4 Spec-Test Contract Reviewer | PENDING | do not self-certify |
| Q6 Production Logic Auditor | PENDING | do not self-certify |
| Difficulty trials | PENDING | tier provisional `advanced` |

## Current blocker

Independent Q4/Q6 in other chats after commit/freeze. Format gate (Q7) and Pre-LLMaJ still open.

## Next action

Commit the rework on `task/cobol-comp3-python-equiv` when authorized, then open packet-bound Q4 and Q6 in fresh chats.
## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Verifier checks decimals/bytes against sealed expected; oracle implements real COMP-3.
- `git apply` outside `/app/.git` is not trusted; not applicable here (Python install oracle).
- Q4/Q6 must not be self-certified from the producer chat.
