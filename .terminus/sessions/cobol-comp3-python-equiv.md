# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/cobol-comp3-python-equiv-completion`
- Pull request: `#22`
- Current task commit: `d2bf8685258c89fbe9db77531788c56c2bef15a8`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Creation Controller policy: `1.0`

## Current task profile

Software/Languages warehouse SKU tape unpacker for signed/unsigned COMP-3, REDEFINES, and OCCURS DEPENDING ON. Solver-visible runtime remains intentionally compact and uses the non-strict `large_system` authoring profile; do not pad LOC to satisfy scale diagnostics. Holdouts and malformed-record cases are verifier-only. No GnuCOBOL runtime is required.

This task has completed one consolidated repair/refreeze after the exhaustive Q4 REVISE at `bf242838a5a985583d43e9ca919c03e4c3f9459d`. A correctly packet-bound replacement Q4 at `d2bf8685...` returned REVISE with four blockers; an independent Adjudicator has now disposed the latent-reviewer-omission question for Q4-STC-003/004. Historical packets/results remain immutable evidence.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`; prior consolidated repair |
| Q2 Verifier Coverage Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`; prior consolidated repair |
| Q3 Spec Ambiguity Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`; prior consolidated repair |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Creator Complexity Gate | PASS | run `31815982777`, job `94817651950`; task-specific PASS, unrelated workflow baseline failure later |
| Preflight/static | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Ruff verifier | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Oracle = 1 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086` |
| NOP = 0 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086` |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-spec-test-contract-73aef64c20.json`; `REVISE/HIGH/SUFFICIENT`; result commit `94db2ab2537217f106700166a8450b4c6a83f316`; blockers Q4-STC-001..004 |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-production-logic-f50b73e14c.json`; `PASS/HIGH/SUFFICIENT`; result commit `036080cbe45e3c17b776648b26975516d71b5e5f`; scope `3935f9e2a3b0898368c4a56cae822a2769cabb73d18a7c300d8d9decda5ddb45` |
| Adjudication | REQUEST_CHANGES | `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.json`; `REQUEST_CHANGES/HIGH/SUFFICIENT`; result commit `515d6efd1c8f0757750ea1f6b36599cc7ab7703d` |
| Quality Interlock | BLOCKED | controlled remediation required for current Q4-STC-001..004, then one new packet-bound Q4; Q6 may be reused only if its recomputed production scope hash remains unchanged |

## Current Q4 / adjudication disposition

- `Q4-STC-001` — normal remediation. The main instruction removed the offline/no-model-API requirement but referenced `ops/handoff.md` still contains `Offline only — no model API, no GnuCOBOL install.` Remove the unintended normative delegated restriction or deliberately contract/enforce it. Current task policy is public network, so the intended remediation is to remove that delegated MUST.
- `Q4-STC-002` — normal remediation. Current malformed-record tests still grade nonempty error/recovery/byte-length conventions more tightly than `record-layout.md` uniquely specifies. Align verifier and public failure interface at externally observable semantics, preferring implementation freedom over private recovery mechanics.
- `Q4-STC-003` — Adjudicator UPHELD / MEDIUM / `LATENT_REVIEWER_OMISSION`. The incident-evidence P2P existence test was already present unchanged at `bf242838` while the instruction never imposed a final-state preservation obligation. Controlled remediation is required; no-drip classification does not waive the defect.
- `Q4-STC-004` — Adjudicator UPHELD / MEDIUM with mixed classification. `redefines_ok` is a pure latent reviewer omission. `odo_lengths_ok` contains a latent semantic gap plus a remediation-touched verifier manifestation because the prior incorrect invalid-ODO false assertion was removed. Controlled remediation is required; do not replace direct ODO/REDEFINES behavioral checks with self-reported booleans.

## Current deterministic evidence

- Edition-3 run `31815982778`, job `94817751331`: Preflight PASS, Ruff PASS, Oracle reward `1`, NOP reward `0` on `d2bf8685...`.
- Artifact `9225067086` (`sha256:acd30e9c854cf8dfa2c48ec43ddc649b319c2f393fcd5f247f2ffdbea98cb0c5`) contains Oracle/NOP validation evidence.
- Creator Complexity run `31815982777`, job `94817651950`: this task PASS; `tests_total=27`, `f2p=25`, `p2p=2`, `unclassified=0`, `requirements=6`.
- Current Q6 PASS is exact-commit current at `d2bf8685...`; after remediation it can survive only if packet/result/current production `review_scope_hash` values remain identical.
- Production Authenticity and Creator global reds remain unrelated repository baseline debt; Harbor has no valid current result because reusable AI credentials return HTTP 401.

## Historical review evidence

- Prior exhaustive Q4 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-spec-test-contract-c1744a7ef9.json` — `REVISE/HIGH/SUFFICIENT`, 5 blocking + 2 advisory findings.
- Prior Q6 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-production-logic-b950c2f7a4.json` — historical only.
- A later chat accidentally reviewed the old `bf242838...` packet and correctly refused to overwrite its existing result. That execution is `STALE/NON_ADVANCING`.

## Current canonical review evidence

- Replacement Q4 result: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-spec-test-contract-73aef64c20.json`.
- Replacement Q6 result: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-production-logic-f50b73e14c.json`.
- Adjudication packet: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.packet.json`.
- Adjudication result: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.json`.

## Current blocker

A single controlled remediation must address all four current Q4 blockers together. After remediation: commit/refreeze the task, rerun deterministic task validation, recompute Q6 production scope, preserve Q6 only if the scope hash is unchanged, generate one fresh Q4 packet, and run one final independent exhaustive Q4. Do not restart another blind narrow-patch loop.

## Next action

Fix Q4-STC-001..004 as one bounded remediation. Prefer removing unintended/unverifiable normative prose and circular self-diagnostic guarantees rather than adding hidden grading constraints. Keep direct COMP-3/ODO/REDEFINES behavioral coverage. Rerun Oracle/NOP and Q4-alignment validation, refreeze, then generate exactly one new Q4 packet. Q6 does not rerun if its production-scope hash remains `3935f9e2a3b0898368c4a56cae822a2769cabb73d18a7c300d8d9decda5ddb45`.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; every digit nibble is 0-9 and required storage pad nibbles are zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Only unknown-flag exit 2 is a stable CLI exit contract; malformed-record process exit 1 is implementation behavior unless intentionally contracted later.
- Report tests grade documented semantics, not JSON whitespace/key ordering or internal error-message wording.
- The task does not intentionally require offline/no-model-API/GnuCOBOL prohibition; current network policy remains `public`.
- Do not create a preservation obligation for incident notes merely to justify a P2P test; remove the nonessential grading check unless preservation is genuinely required.
- Do not use circular `odo_lengths_ok` / `redefines_ok` booleans as substitutes for direct behavioral verifier checks.
- Never reuse stale Q4/Harbor evidence as current acceptance.
- Never dispatch a semantic review packet unless `.terminus/validate_review_invocation.py` reports `REVIEW_INVOCATION_READY` or equivalent checks are independently established.
- Do not self-certify independent Q4 results in this conversation.
- Do not broaden this task to unrelated repository baseline debt.
- PR #22 stays draft/unmerged until mandatory workflow evidence is current.
