# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `VALIDATING`
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

The abandoned branch `task/cobol-comp3-python-equiv@51723cbca1013fea7b1f7ca3cf0583af7182c785` was 483 commits behind current main. Useful task-only hardening was recovered onto the current branch; its old reviews and Harbor runs remain historical only.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: Q4-STC-001/002/005 aligned by removing undocumented malformed-record exit assumptions, matching summary domains to the public contract, and removing the unnecessary offline/model-API MUST |
| Q2 Verifier Coverage Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: Q4-STC-003/004 plus A01/A02 repaired; test map now has 27 cases (25 F2P / 2 P2P) including non-decimal digit nibble, required report schema, indeterminate byte_length=0, semantic rerun, and wording-independent error checks |
| Q3 Spec Ambiguity Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: verifier no longer grades undocumented exit-1, JSON byte formatting, error prose, widened padding summary, or invalid-count ODO summary semantics |
| Q7 Task Format Enforcer | PENDING | fresh current-task CI required after Q4 remediation |
| Creator Complexity Gate | PENDING | fresh current-task CI required; non-strict profile retained |
| Preflight/static | PENDING | old run is stale after task change |
| Ruff verifier | PENDING | old run is stale after task change |
| Oracle = 1 | PENDING | old 24-test run is stale; current verifier has 27 mapped tests |
| NOP = 0 | PENDING | old 24-test run is stale; current verifier has 27 mapped tests |
| Q4 Spec-Test Contract Reviewer | STALE | prior result `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-spec-test-contract-c1744a7ef9.json` was `REVISE/HIGH/SUFFICIENT`; all 5 blockers and 2 advisories received one consolidated remediation cycle |
| Q6 Production Logic Auditor | STALE | prior result `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-production-logic-b950c2f7a4.json` was `PASS/HIGH/SUFFICIENT`; task.toml and solver-visible environment contract changed, so production scope must be re-audited rather than reused |
| Quality Interlock | PENDING | re-freeze only after fresh deterministic evidence, then one replacement Q4 and Q6 review |

## Q4 remediation disposition

- `Q4-STC-001` — fixed by removing verifier assertions on process exit 1 for malformed records; the documented unknown-flag exit 2 contract remains tested.
- `Q4-STC-002` — fixed by keeping summary assertions within the documented domains: wrong sign affects `comp3_signed_ok`; invalid padding/digit and invalid ODO count are asserted as record errors without inventing broader summary meanings.
- `Q4-STC-003` — fixed with `test_f2p_comp3_rejects_nondecimal_digit_nibble`, mutating a QOH digit nibble to `A` while keeping sign/pad/framing otherwise valid.
- `Q4-STC-004` — fixed with exact default `source_records`, record `index`, success `error: null`, required field/type coverage, and a truncated record proving indeterminate `byte_length: 0`.
- `Q4-STC-005` — fixed by removing the unnecessary offline/no-model-API requirement from both the work request and delegated layout contract; live Terminus policy keeps `network_mode = "public"` by default for this task.
- `Q4-STC-A01` — fixed by semantic JSON equality on rerun instead of byte-identical serialization.
- `Q4-STC-A02` — fixed by requiring a non-empty documented error string without prescribing internal message vocabulary.

## Historical evidence

- Frozen task `bf242838a5a985583d43e9ca919c03e4c3f9459d`: Edition-3 run `31808250840`, job `94792334675`, artifact `9222093520` had preflight/Ruff PASS, Oracle 24/24 reward 1, NOP reward 0. This evidence is now stale after remediation.
- Historical Q4 result commit `29c09f765e69a88f30dc5daf5ada2c6740e4baa3`: `REVISE/HIGH/SUFFICIENT`, 5 blocking + 2 advisory findings.
- Historical Q6 result commit `81e5de78e5ae224b033415283bd2a665acc267ae`: `PASS/HIGH/SUFFICIENT`, no findings. It is not reused because the production scope changed.
- Repository-wide `platform-sonar`, stale-session, `wiki-creation-counter-flap`, Production Authenticity policy-marker, and Harbor credential issues remain unrelated baseline/infrastructure debt and are not task remediation targets.

## Current blocker

Fresh deterministic validation of task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8` is required before re-freeze. Oracle must pass all 27 current tests and NOP must remain reward 0.

## Next action

Consume the latest Edition-3 and Creator Complexity runs for current task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`. If task-owned gates pass, freeze once, generate replacement packet-bound Q4 and Q6 reviews, and do not start another ordinary remediation cycle unless Protocol 2.2 explicitly permits it.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; every digit nibble is 0-9 and required storage pad nibbles are zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Malformed-record process exit 1 is implementation behavior, not a public graded contract; only unknown-flag exit 2 is stable.
- Report tests grade documented semantics, not JSON whitespace/key ordering or internal error-message wording.
- The task does not require offline/no-model-API operation; live network policy remains `public`.
- Never reuse stale Q4/Q6/Harbor evidence as current acceptance.
- Do not self-certify independent Q4/Q6 results.
- Do not broaden this task to unrelated repository baseline debt.
- This is the single consolidated repair/refreeze cycle allowed after the exhaustive Q4 REVISE.
