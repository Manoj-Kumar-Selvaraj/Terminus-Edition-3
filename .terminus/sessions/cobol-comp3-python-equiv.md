# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `SPEC_ALIGNMENT`
- Working branch: `task/cobol-comp3-python-equiv-completion`
- Pull request: pending
- Current task-content commit: `987b6450bac6d49d7ebe7965fb98a6845f302673`
- Control-plane base: `main@1b42a75a40977919d567fc6d38b80cb58e17b2b7`
- Agent-system policy: `2.4`
- Creation Controller policy: `1.0`

## Current task profile

Software/Languages warehouse SKU tape unpacker for signed/unsigned COMP-3, REDEFINES, and OCCURS DEPENDING ON. Solver-visible runtime remains intentionally compact and uses the non-strict `large_system` authoring profile; do not pad LOC to satisfy scale diagnostics. Holdouts and malformed-record cases are verifier-only. No model API or GnuCOBOL runtime is required.

The abandoned branch `task/cobol-comp3-python-equiv@51723cbca1013fea7b1f7ca3cf0583af7182c785` was 483 commits behind current main. Useful task-only hardening was recovered onto the current branch; its old Q4/Q6 packets were not carried forward because they are commit-bound and stale.

## Current deterministic evidence

- Reference public tape: PASS — two records, byte lengths `44` and `28`, summary flags true.
- Reference sealed holdout: PASS — two records, byte lengths `60` and `28`, negative/scaled COMP-3 and ODO behavior correct.
- Strict malformed COMP-3 probes: PASS — signed field rejects `F`; unsigned field rejects `C` and `D`; non-zero left storage pad is rejected while the parser preserves the 44-byte record boundary.
- Existing malformed fixtures: PASS — illegal sign and out-of-range ODO become record errors.
- Current complexity manifest/test-map shape reconciled to the live `validate_task_complexity.py` contract; non-strict scale shortfalls are diagnostic, while structural topology/test mapping is designed to pass.

## Gate status

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | IN_PROGRESS | recovered contract + new sign-class/pad coverage |
| Q2 Verifier Coverage Repair | IN_PROGRESS | 22 F2P / 2 P2P across current test map |
| Q3 Adversarial Robustness | IN_PROGRESS | malformed sign class, pad, sign nibble, ODO |
| Q7 Task Format Enforcer | PENDING | run on current branch/PR |
| Complexity / Runtime deterministic gates | PENDING | run on current branch/PR |
| Oracle = 1 | STALE | historical PASS only at `32de80a57ddbc38acd33d36cac598c69abe99da8`; must rerun after current changes |
| NOP = 0 | STALE | historical PASS only at `32de80a57ddbc38acd33d36cac598c69abe99da8`; must rerun after current changes |
| Q4 Spec-Test Contract Reviewer | NOT_STARTED | generate only after current freeze; one bounded independent interlock |
| Q6 Production Logic Auditor | NOT_STARTED | generate only after current freeze; one bounded independent interlock |

## Current blocker

Current-branch deterministic CI plus fresh Oracle/NOP evidence. Historical Harbor evidence proves the older task shape separated oracle from no-op, but it is not acceptance evidence for `987b6450...`.

## Next action

Open a draft PR from the completion branch, run current repository CI and repair only concrete deterministic failures. Then rerun Oracle/NOP on the exact resulting task commit. Freeze once, followed by the bounded Q4/Q6 quality interlock required by the live workflow.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Verifier checks behavior and byte boundaries against sealed expected data; the reference implementation performs genuine COMP-3 decoding.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; storage pad nibbles must be zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Never reuse the old branch's Q4/Q6 packets or Harbor runs as fresh acceptance evidence.
- Do not self-certify independent Q4/Q6 results.
