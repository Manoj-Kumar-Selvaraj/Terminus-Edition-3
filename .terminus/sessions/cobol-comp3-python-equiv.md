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

This is the single consolidated repair/refreeze after the exhaustive Q4 REVISE at `bf242838a5a985583d43e9ca919c03e4c3f9459d`. Historical packets/results remain evidence of that prior cycle only.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: Q4-STC-001/002/005 aligned by removing undocumented malformed-record exit assumptions, matching summary domains to the public contract, and removing the unnecessary offline/model-API MUST |
| Q2 Verifier Coverage Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: 27 mapped tests, 25 F2P / 2 P2P; added non-decimal digit, stable report-schema, indeterminate-length and semantic-rerun coverage; error prose is no longer graded |
| Q3 Spec Ambiguity Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: verifier no longer grades undocumented exit-1, JSON byte formatting, error prose, widened padding summary, or invalid-count ODO summary semantics |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31815982778`, job `94817751331`: preflight accepted the remediated task package |
| Creator Complexity Gate | PASS | run `31815982777`, job `94817651950`: this task PASS with 10 defects, 4 root causes, 9 causal edges, 27 mapped tests (25 F2P / 2 P2P); workflow later fails unrelated `wiki-creation-counter-flap` |
| Preflight/static | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Ruff verifier | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Oracle = 1 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086`: current verifier suite reward 1; Creator gate confirms 27 mapped/unclassified=0 tests and test.sh runs both verifier modules |
| NOP = 0 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086`: reward 0 |
| Q4 Spec-Test Contract Reviewer | PENDING | replacement packet/result required for exact remediated task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8` |
| Q6 Production Logic Auditor | PENDING | replacement packet/result required because solver-visible production scope changed during Q4 remediation |
| Quality Interlock | PENDING | replacement Q4 PASS + replacement Q6 PASS required; no second ordinary remediation loop |

## Q4 remediation disposition

- `Q4-STC-001` — fixed by removing verifier assertions on process exit 1 for malformed records; documented unknown-flag exit 2 remains tested.
- `Q4-STC-002` — fixed by keeping summary assertions within documented domains: wrong sign affects `comp3_signed_ok`; invalid padding/digit and invalid ODO count are asserted as record errors without invented summary meanings.
- `Q4-STC-003` — fixed with `test_f2p_comp3_rejects_nondecimal_digit_nibble`, mutating a QOH digit nibble to `A` while sign/pad/framing remain valid.
- `Q4-STC-004` — fixed with exact default `source_records`, record `index`, success `error: null`, required field/type coverage, and a truncated record proving indeterminate `byte_length: 0`.
- `Q4-STC-005` — fixed by removing the unnecessary offline/no-model-API requirement from the work request and delegated layout contract; `network_mode = "public"` remains the task environment policy.
- `Q4-STC-A01` — fixed by semantic JSON equality on rerun instead of byte-identical serialization.
- `Q4-STC-A02` — fixed by requiring a non-empty error string without prescribing internal message vocabulary.

## Current deterministic evidence

- Edition-3 run `31815982778`, job `94817751331`: Preflight PASS, Ruff PASS, Oracle reward `1`, NOP reward `0`.
- Artifact `9225067086` (`sha256:acd30e9c854cf8dfa2c48ec43ddc649b319c2f393fcd5f247f2ffdbea98cb0c5`) contains current Oracle/NOP validation evidence.
- Creator Complexity run `31815982777`, job `94817651950`: `cobol-comp3-python-equiv` PASS; `tests_total=27`, `f2p=25`, `p2p=2`, `unclassified=0`, `requirements=6`.
- Edition-3 run turns red only after deterministic acceptance, while preparing reusable AI credentials: STB/Snorkel login returns HTTP 401. No Harbor LLMaJ result is claimed.
- Production Authenticity remains unrelated repository-policy baseline debt; Creator Complexity overall red remains unrelated `wiki-creation-counter-flap` debt.

## Historical review evidence

- Q4 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-spec-test-contract-c1744a7ef9.json` — `REVISE/HIGH/SUFFICIENT`, 5 blocking + 2 advisory findings, commit `29c09f765e69a88f30dc5daf5ada2c6740e4baa3`.
- Q6 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-production-logic-b950c2f7a4.json` — `PASS/HIGH/SUFFICIENT`, no findings, commit `81e5de78e5ae224b033415283bd2a665acc267ae`.
- The old Q6 result is not reused because `task.toml` and solver-visible `environment/equiv/docs/record-layout.md` changed, so the conservative production-scope hash changed.

## Current blocker

Exactly one replacement packet-bound Q4 review and one replacement packet-bound Q6 review are required for the remediated frozen candidate. Harbor LLMaJ remains separately blocked by invalid/missing reusable AI credentials.

## Next action

Derive current Q4/Q6 role hashes plus the new Q6 production-scope hash from the canonical review contract, generate immutable replacement packets for task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`, then run Q4 and Q6 once each in fresh independent chats. If the replacement Q4 raises a material finding on evidence unchanged and fully reviewable in the previous exhaustive Q4 scope, classify it `LATENT_REVIEWER_OMISSION` and route to Adjudicator rather than beginning another ordinary repair loop.

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
