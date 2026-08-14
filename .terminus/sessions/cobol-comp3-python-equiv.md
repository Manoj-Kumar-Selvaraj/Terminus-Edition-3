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
| Q1 Spec Gap Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: prior Q4-STC-001/002/005 remediation removed undocumented malformed exit assumptions, narrowed summary domains, and removed the work-request/layout offline MUST |
| Q2 Verifier Coverage Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: 27 mapped tests, 25 F2P / 2 P2P; added non-decimal digit, stable report-schema, indeterminate-length and semantic-rerun coverage |
| Q3 Spec Ambiguity Repair | PASS | task commit `d2bf8685258c89fbe9db77531788c56c2bef15a8`: verifier no longer grades undocumented exit-1, JSON byte formatting, internal error wording, widened padding summary, or invalid-count ODO summary semantics |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31815982778`, job `94817751331`: preflight accepted the remediated task package |
| Creator Complexity Gate | PASS | run `31815982777`, job `94817651950`: this task PASS with 10 defects, 4 root causes, 9 causal edges, 27 mapped tests (25 F2P / 2 P2P); workflow later fails unrelated `wiki-creation-counter-flap` |
| Preflight/static | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Ruff verifier | PASS | Edition-3 run `31815982778`, job `94817751331` |
| Oracle = 1 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086`: current verifier suite reward 1 |
| NOP = 0 | PASS | Edition-3 run `31815982778`, job `94817751331`, artifact `9225067086`: reward 0 |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-spec-test-contract-73aef64c20.json`, commit `94db2ab2537217f106700166a8450b4c6a83f316`: HIGH/SUFFICIENT, four blocking findings |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-production-logic-f50b73e14c.json`, commit `036080cbe45e3c17b776648b26975516d71b5e5f`: HIGH/SUFFICIENT, no findings, scope `3935f9e2a3b0898368c4a56cae822a2769cabb73d18a7c300d8d9decda5ddb45` |
| Q4 latent-omission adjudication | PENDING | generated packet `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.packet.json`; dispute limited to current Q4-STC-003 and Q4-STC-004 |
| Quality Interlock | BLOCKED | Q4-STC-001/002 require normal remediation; Q4-STC-003/004 require Adjudicator disposition before any further repair under Protocol 2.2 no-drip rule |

## Current Q4 disposition

Current replacement Q4 at `d2bf8685...` returned `REVISE/HIGH/SUFFICIENT` with four blocking findings.

- `Q4-STC-001` — `TOUCHED_BY_REPAIR / INCOMPLETE_REMEDIATION`: the main instruction and layout contract removed the prior offline/model-API MUST, but unchanged `/app/equiv/ops/handoff.md` still says `Offline only — no model API, no GnuCOBOL install`. Route normally after adjudication; preferred repair is to remove the non-material normative restriction rather than invent a hidden network/tooling test.
- `Q4-STC-002` — `TOUCHED_BY_REPAIR / MIXED`: old strict packed-field cases already required nonempty errors, `byte_length == 44` and `record_count == 2`, while the consolidated repair retained those recovery semantics and newly added an explicit invalid-ODO `byte_length == 28`. Route normally after adjudication; prefer relaxing verifier-only recovery/boundary assumptions unless the external failure contract is deliberately made stable.
- `Q4-STC-003` — `LATENT_REVIEWER_OMISSION` candidate: `test_p2p_incident_evidence_present` already existed unchanged at `bf242838...`, and the prior exhaustive Q4 explicitly concluded P2P ownership was coherent. Adjudication required before repair.
- `Q4-STC-004` — `LATENT_REVIEWER_OMISSION` candidate: `summary.odo_lengths_ok` and `summary.redefines_ok` false-state definitions and true-only verification were already present at `bf242838...`; the prior exhaustive Q4 did not identify the circular/unverifiable false-state contract. Adjudication required before repair.

## Current deterministic evidence

- Edition-3 run `31815982778`, job `94817751331`: Preflight PASS, Ruff PASS, Oracle reward `1`, NOP reward `0`.
- Artifact `9225067086` (`sha256:acd30e9c854cf8dfa2c48ec43ddc649b319c2f393fcd5f247f2ffdbea98cb0c5`) contains current Oracle/NOP validation evidence.
- Creator Complexity run `31815982777`, job `94817651950`: `cobol-comp3-python-equiv` PASS; `tests_total=27`, `f2p=25`, `p2p=2`, `unclassified=0`, `requirements=6`.
- Current Q6 PASS is exact-task-commit and exact-scope bound. It remains current until any `task.toml` or solver-visible `environment/` change alters the Q6 scope hash.
- Edition-3 run turns red only after deterministic acceptance while preparing reusable AI credentials: STB/Snorkel login returns HTTP 401. No Harbor LLMaJ result is claimed.
- Production Authenticity remains unrelated repository-policy baseline debt; Creator Complexity overall red remains unrelated `wiki-creation-counter-flap` debt.

## Historical review evidence

- Prior exhaustive Q4 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-spec-test-contract-c1744a7ef9.json` — `REVISE/HIGH/SUFFICIENT`, 5 blocking + 2 advisory findings, commit `29c09f765e69a88f30dc5daf5ada2c6740e4baa3`.
- Prior Q6 at `bf242838...`: `.terminus/reviews/cobol-comp3-python-equiv/bf242838/cobol-comp3-python-equiv-bf242838-production-logic-b950c2f7a4.json` — `PASS/HIGH/SUFFICIENT`, no findings, commit `81e5de78e5ae224b033415283bd2a665acc267ae`.
- A later chat mistakenly re-reviewed the old `bf242838...` packet. It refused to overwrite the populated immutable output and is `STALE/NON_ADVANCING`.

## Current review packets/results

- Current Q4 packet: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-spec-test-contract-73aef64c20.packet.json`.
- Current Q4 result: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-spec-test-contract-73aef64c20.json`.
- Current Q6 packet: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-production-logic-f50b73e14c.packet.json`.
- Current Q6 result: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-production-logic-f50b73e14c.json`.
- Current Q6 production scope: `3935f9e2a3b0898368c4a56cae822a2769cabb73d18a7c300d8d9decda5ddb45`.
- Latent-omission Adjudicator packet: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.packet.json`.
- Adjudicator output path: `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.json`.

## Review-dispatch hardening

The control plane now has `.terminus/validate_review_invocation.py` plus regression tests. `.terminus/agents/INVOKE.md` requires a fail-closed pre-dispatch check before semantic inspection. It rejects stale task commits, dirty task state, stale role/scope provenance, packet/result path mismatch, and already-populated immutable result paths.

The generated Adjudicator packet was produced by `.terminus/new_review_packet.py` in GitHub Actions, not hand-written. The temporary packet-generation workflow was removed after capture.

## Current blocker

Run exactly one independent Adjudicator review for Q4-STC-003 and Q4-STC-004 using the generated packet. Do not adjudicate Q4-STC-001/002; they are normal repair-owned findings. Do not change task files before adjudication, because the dispute is bound to frozen task commit `d2bf8685...`.

## Next action

Open one fresh Adjudicator chat using `.terminus/reviews/cobol-comp3-python-equiv/d2bf8685/cobol-comp3-python-equiv-d2bf8685-adjudication-93878871ea.packet.json`. The Adjudicator must independently decide whether Q4-STC-003 and Q4-STC-004 are controlling material defects and whether they are latent reviewer omissions under Protocol 2.2. After that result is frozen, route the upheld findings plus Q4-STC-001/002 into one bounded remediation, rerun affected deterministic gates, preserve or rerun Q6 strictly according to the production scope hash, refreeze, and generate one final Q4 packet.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; every digit nibble is 0-9 and required storage pad nibbles are zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Malformed-record process exit 1 is implementation behavior, not a public graded contract; only unknown-flag exit 2 is stable.
- Report tests grade documented semantics, not JSON whitespace/key ordering or internal error-message wording.
- The task does not require offline/no-model-API operation; live network policy remains `public`.
- Never reuse stale Q4/Q6/Harbor evidence as current acceptance.
- Never dispatch a semantic review packet unless `.terminus/validate_review_invocation.py` reports `REVIEW_INVOCATION_READY` or the equivalent checks are independently established in a remote-only surface.
- Do not self-certify independent reviewer or Adjudicator results.
- Do not broaden this task to unrelated repository baseline debt.
- This is the single consolidated repair/refreeze cycle allowed after the prior exhaustive Q4 REVISE; latent unchanged-scope findings require Adjudicator disposition before another ordinary repair.
