# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/cobol-comp3-python-equiv-completion`
- Pull request: `#22`
- Current task commit: `b3ac4f71d16f0e3528dea1f8a07fc164b78e38a4`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Creation Controller policy: `1.0`

## Current task profile

Software/Languages warehouse SKU tape unpacker for signed/unsigned COMP-3, REDEFINES, and OCCURS DEPENDING ON. Solver-visible runtime remains intentionally compact under the non-strict `large_system` profile. Holdouts and malformed-record cases are verifier-only.

The `73d67e25...` candidate received a current packet-bound Q6 PASS and a current packet-bound Q4 REVISE with exactly two verifier-coverage findings. Those two Q4 findings have now been repaired with tests-only changes and refrozen at `b3ac4f71d16f0e3528dea1f8a07fc164b78e38a4`.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | solver-visible instruction/delegated contract unchanged and aligned; final Q4 at `73d67e25...` found only verifier-coverage gaps |
| Q2 Verifier Coverage Repair | PASS | current `b3ac4f71...`: semantic alternate-layout coverage plus determinable malformed-record byte length coverage added; 27 mapped tests remain classified |
| Q3 Spec Ambiguity Repair | PASS | no new requirement or contract ambiguity introduced by tests-only remediation |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31825517203`, job `94848636241`: Preflight PASS |
| Creator Complexity Gate | PASS | prior task-specific PASS remains structurally applicable; no task topology/test-map classification names changed |
| Preflight/static | PASS | Edition-3 run `31825517203`, job `94848636241` |
| Ruff verifier | PASS | Edition-3 run `31825517203`, job `94848636241` |
| Oracle = 1 | PASS | Edition-3 run `31825517203`, job `94848636241`, artifact `9228682223` |
| NOP = 0 | PASS | Edition-3 run `31825517203`, job `94848636241`, artifact `9228682223` |
| Q4 Spec-Test Contract Reviewer | PENDING | final packet `.terminus/reviews/cobol-comp3-python-equiv/b3ac4f71/cobol-comp3-python-equiv-b3ac4f71-spec-test-contract-53435e2c6e.packet.json`; output absent before dispatch |
| Q6 Production Logic Auditor | PASS | reusable current PASS `.terminus/reviews/cobol-comp3-python-equiv/73d67e25/cobol-comp3-python-equiv-73d67e25-production-logic-256d230311.json`; production scope unchanged at `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff` |
| Quality Interlock | PENDING | requires the final `b3ac4f71...` Q4 PASS; Q6 is already current through validated scope reuse |

## Final verifier-only Q4 remediation

- `Q4-001` — strengthened `test_f2p_layout_override_is_honored`. The verifier now supplies a genuinely different 9-byte layout (`X(4)`, display `9(2)`, signed `S9(3)V9 COMP-3`) and matching record bytes, then asserts decoded fields and layout-derived byte length. An evaluator that hard-codes the SKU layout while reading only the alternate layout ID cannot pass.
- `Q4-002` — complete malformed packed records now assert the determinable first-record boundary `byte_length == 44`. This covers the documented determinable-length branch without requiring any specific continuation/recovery behavior or reintroducing an exact invalid-ODO recovery length.
- No `instruction.md`, `task.toml`, `environment/`, solution, or implementation file changed in this remediation.

## Current deterministic evidence

- Edition-3 run `31825517203`, job `94848636241`: Preflight PASS, Ruff PASS, Oracle reward `1`, NOP reward `0`.
- Artifact `9228682223`, SHA-256 `fef9496d804886cbabcdd2312a9347d90b46564d30a816e7edcf7d812fd0f063`.
- The Edition-3 job fails only after deterministic acceptance at reusable AI credential preparation; Harbor LLMaJ is skipped and no Harbor PASS is claimed.
- Q6 scope-reuse probe run `31825710965`, job `94849229064` recomputed current Q6 scope as `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff`, exactly matching the recorded PASS result, and emitted `Q6_SCOPE_REUSE_READY`.

## Review evidence

- Q4 at `73d67e25...`: `.terminus/reviews/cobol-comp3-python-equiv/73d67e25/cobol-comp3-python-equiv-73d67e25-spec-test-contract-d809ade313.json` — `REVISE/HIGH/SUFFICIENT`, exactly two blocking verifier-coverage findings; stale after current tests-only repair.
- Q6 at `73d67e25...`: `.terminus/reviews/cobol-comp3-python-equiv/73d67e25/cobol-comp3-python-equiv-73d67e25-production-logic-256d230311.json` — `PASS/HIGH/SUFFICIENT`, scope `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff`; remains current by Protocol 2.2 scope reuse.
- Final Q4 packet: `.terminus/reviews/cobol-comp3-python-equiv/b3ac4f71/cobol-comp3-python-equiv-b3ac4f71-spec-test-contract-53435e2c6e.packet.json`.
- Final Q4 review ID: `cobol-comp3-python-equiv-b3ac4f71-spec-test-contract-53435e2c6e`.
- Final Q4 role contract: `0c40044ec13f0109a5526301cac6e5d2f52f5596d006bee2cdcaa90c0771d7f6`.

## Current blocker

Exactly one final independent Q4 review is required against task commit `b3ac4f71d16f0e3528dea1f8a07fc164b78e38a4`. Q6 does not rerun because its recomputed production-scope hash is unchanged and the existing PASS satisfies the current role contract.

## Next action

Run the pre-dispatch invocation guard for the final Q4 packet, then dispatch exactly one fresh independent Q4. If it returns PASS with non-LOW confidence and SUFFICIENT evidence, validate provenance and mark the Quality Interlock PASS before proceeding to downstream mandatory stages.

## Decisions that must survive chat changes

- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; digit nibbles are 0-9 and required storage pad nibbles are zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Unknown-flag exit 2 is the only stable CLI process-exit requirement.
- Malformed record errors are non-empty strings; verifier does not grade private wording or require a particular continuation strategy.
- When a malformed complete record boundary remains determinable, the report must carry that actual byte length; `0` is reserved for indeterminate boundaries.
- ODO and REDEFINES correctness are graded directly, not through circular summary booleans.
- Incident/handoff notes are context, not preservation targets.
- Exact default inputs are `/app/equiv/programs/skumast.layout` and `/app/equiv/samples/sku-public.dat`; `--layout PATH` must drive actual parsing semantics.
- Current task network policy is `public`; no offline/model-API/GnuCOBOL prohibition is a solver requirement.
- Never reuse stale Q4/Harbor evidence as current acceptance.
- Q6 may be reused only while the validated production scope remains exactly `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff` and the Q6 role contract remains current.
- Do not self-certify independent Q4 results in this conversation.
- Do not broaden this task to unrelated repository baseline debt.
- PR #22 stays draft/unmerged until mandatory workflow evidence is current.
