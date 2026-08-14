# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/cobol-comp3-python-equiv-completion`
- Pull request: `#22`
- Current task commit: `73d67e25347ee8f5802a7194518dc197a43a9f65`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Creation Controller policy: `1.0`

## Current task profile

Software/Languages warehouse SKU tape unpacker for signed/unsigned COMP-3, REDEFINES, and OCCURS DEPENDING ON. Solver-visible runtime remains intentionally compact and uses the non-strict `large_system` authoring profile; do not pad LOC to satisfy scale diagnostics. Holdouts and malformed-record cases are verifier-only.

The prior frozen candidate `d2bf8685...` received a correctly packet-bound Q4 REVISE with four blockers and Q6 PASS. Independent Adjudication upheld Q4-STC-003 and Q4-STC-004 and authorized controlled remediation under Protocol 2.2's no-drip rule. That remediation is complete and refrozen at `73d67e25347ee8f5802a7194518dc197a43a9f65`.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | current task commit `73d67e25347ee8f5802a7194518dc197a43a9f65`; solver-visible contract and instruction aligned |
| Q2 Verifier Coverage Repair | PASS | current task commit: 27 mapped tests, 26 F2P / 1 P2P, 0 unclassified; phantom incident-preservation test replaced by real `--layout` override coverage |
| Q3 Spec Ambiguity Repair | PASS | malformed-record grading no longer requires private recovery boundaries; circular ODO/REDEFINES summary false-state promises removed |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31823590134`, job `94842430458`: Preflight PASS |
| Creator Complexity Gate | PASS | run `31823590149`, job `94842385495`: this task PASS with 27 tests / 26 F2P / 1 P2P / 6 requirements / 0 unclassified; workflow later fails unrelated `wiki-creation-counter-flap` |
| Preflight/static | PASS | Edition-3 run `31823590134`, job `94842430458` |
| Ruff verifier | PASS | Edition-3 run `31823590134`, job `94842430458` |
| Oracle = 1 | PASS | Edition-3 run `31823590134`, job `94842430458`, artifact `9227958973` |
| NOP = 0 | PASS | Edition-3 run `31823590134`, job `94842430458`, artifact `9227958973` |
| Q4 Spec-Test Contract Reviewer | PENDING | packet `.terminus/reviews/cobol-comp3-python-equiv/73d67e25/cobol-comp3-python-equiv-73d67e25-spec-test-contract-d809ade313.packet.json`; pre-dispatch guard `REVIEW_INVOCATION_READY` in run `31823947548`, job `94843524016` |
| Q6 Production Logic Auditor | PENDING | packet `.terminus/reviews/cobol-comp3-python-equiv/73d67e25/cobol-comp3-python-equiv-73d67e25-production-logic-256d230311.packet.json`; scope `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff`; pre-dispatch guard `REVIEW_INVOCATION_READY` in run `31823947548`, job `94843524016` |
| Quality Interlock | PENDING | fresh current Q4 PASS + fresh current Q6 PASS required |

## Controlled Q4 remediation completed

- `Q4-STC-001` — removed the stale `Offline only — no model API, no GnuCOBOL install` MUST from referenced `ops/handoff.md`; task network policy remains `public`.
- `Q4-STC-002` — retained the public non-empty record-error contract, but removed verifier assertions that malformed packed fields must recover a 44-byte boundary, continue to a second record, or that invalid ODO must report exactly 28 bytes. Truncation still proves the contracted indeterminate `byte_length: 0` branch.
- `Q4-STC-003` — removed grading of incident/handoff/documentation file preservation. The legitimate runtime layout/sample P2P check remains.
- `Q4-STC-004` — removed `odo_lengths_ok` and `redefines_ok` from the stable required report contract and verifier schema assertions. Direct ODO byte-length and REDEFINES alias behavior remain the authoritative behavioral checks.
- Proactive hardening — `instruction.md` now names exact default layout/sample files and exact C/D-versus-F sign classes; a new F2P test uses an alternate `LAYOUT SKU-OVERRIDE` file to prove `--layout PATH` is actually honored.

## Current deterministic evidence

- Edition-3 run `31823590134`, job `94842430458`: Preflight PASS, Ruff PASS, Oracle reward `1`, NOP reward `0`.
- Artifact `9227958973`, SHA-256 `ac502242a7768bd2545064c051035b541ce50c5e1e5cd0541ae441b2d0e17b39`.
- Edition-3 fails only at reusable AI credential preparation; Harbor LLMaJ is skipped and no Harbor PASS is claimed.
- Creator Complexity run `31823590149`, job `94842385495`: `cobol-comp3-python-equiv` PASS; `tests_total=27`, `f2p=26`, `p2p=1`, `unclassified=0`, `requirements=6`. Global workflow failure remains unrelated `wiki-creation-counter-flap` debt.

## Review packet provenance

- Q4 review ID: `cobol-comp3-python-equiv-73d67e25-spec-test-contract-d809ade313`.
- Q4 role contract: `0c40044ec13f0109a5526301cac6e5d2f52f5596d006bee2cdcaa90c0771d7f6`.
- Q4 output path is currently absent.
- Q6 review ID: `cobol-comp3-python-equiv-73d67e25-production-logic-256d230311`.
- Q6 role contract: `8eb84a3715c4805f762325ceaa890339fc966a2a475cb58986578a15418c5378`.
- Q6 production scope: `5272db80b02b8cf40fb5435617d12a831755e11847597fbcc28f18986d069dff`.
- Q6 output path is currently absent.
- Both packets record control-plane commit `83f38b8f0be9abfc1f86803789de8b2dbc4c28bd` and passed `.terminus/validate_review_invocation.py` before handoff.

## Historical semantic evidence

- Exhaustive Q4 at `bf242838...`: historical REVISE only.
- Replacement Q4 at `d2bf8685...`: `REVISE/HIGH/SUFFICIENT`; stale after controlled remediation.
- Replacement Q6 at `d2bf8685...`: `PASS/HIGH/SUFFICIENT`; stale because production scope changed.
- Adjudication at `d2bf8685...`: `REQUEST_CHANGES/HIGH/SUFFICIENT`; controlled remediation completed.

## Current blocker

Run exactly one fresh independent Q4 and one fresh independent Q6 against the prepared `73d67e25...` packets. Do not reuse the stale `d2bf8685...` results as acceptance evidence.

## Next action

Dispatch the two prepared packets in separate fresh chats. If both return PASS with non-LOW confidence and SUFFICIENT evidence, validate result provenance and advance Quality Interlock. Do not start another ordinary Q4 remediation loop without Protocol circuit-breaker disposition.

## Decisions that must survive chat changes

- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; every digit nibble is 0-9 and required storage pad nibbles are zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Unknown-flag exit 2 is the only stable CLI process-exit requirement.
- Malformed record errors are non-empty strings; tests do not grade private wording or a mandatory recovery/continuation strategy.
- ODO and REDEFINES correctness are graded directly, not through circular summary booleans.
- Incident/handoff notes are context, not preservation targets.
- Exact default inputs are `/app/equiv/programs/skumast.layout` and `/app/equiv/samples/sku-public.dat`; CLI path overrides must work.
- Current task network policy is `public`; no offline/model-API/GnuCOBOL prohibition is a solver requirement.
- Never reuse stale Q4/Q6/Harbor evidence as current acceptance.
- Never dispatch a semantic packet unless `.terminus/validate_review_invocation.py` reports `REVIEW_INVOCATION_READY` or equivalent checks are independently established.
- Do not self-certify independent Q4/Q6 results in this conversation.
- Do not broaden this task to unrelated repository baseline debt.
- PR #22 stays draft/unmerged until mandatory workflow evidence is current.
