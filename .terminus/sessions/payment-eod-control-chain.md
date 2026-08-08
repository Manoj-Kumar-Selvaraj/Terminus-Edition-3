# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ_PASS`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2` (validation trigger only; do not merge)
- Frozen task content commit on `main`: `84d4436f027f1ba1dd6ac909f31aae3aaafe9554`
- Applicable validation merge ref: `20b2da2438865bffb9b9c0c9dbbfb9c75edbb00a`
- Applicable PR head: `4dd807e64ec82cbda09c3717001ccb5c1ae78e74`
- Agent-system policy: `2.2`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.0`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `UNVERIFIED` until final acceptance refresh

## Current large-system profile

Creator Complexity Gate run `31260035557` (#28) on merge ref `20b2da2438865bffb9b9c0c9dbbfb9c75edbb00a` reports:

- substantive solver-visible LOC: `3055`
- defect manifestations: `29`
- root-cause clusters: `6`
- interrelated manifestations: `29`
- causal edges: `27`
- verifier tests: `37`
- F2P: `30`
- P2P: `7`
- unclassified: `0`

The final 30/7 classification is empirically confirmed by the NOP artifact: all seven `test_p2p_*` cases pass the starter and all 30 F2P cases fail it.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | run `31260035557` (#28), job `93109314028`; 3055 LOC / 29 defects / 6 roots / 37 tests / 30 F2P / 7 P2P |
| Preflight/static | PASS | Terminus CI run `31260035556` (#150), merge ref `20b2da243...` |
| Ruff verifier | PASS | run `31260035556` (#150) |
| STB/Docker setup | PASS | run `31260035556` (#150); direct Harbor utility-agent path available |
| Oracle = 1 | PASS | run `31260035556` (#150), direct Harbor utility agent; 37/37 pytest PASS; reward `1`; 0 gate exceptions |
| NOP = 0 | PASS | run `31260035556` (#150), direct Harbor utility agent; 30 F2P fail + 7 P2P pass; reward `0`; 0 gate exceptions |
| Validation evidence artifact | PASS | artifact `9022556589`, `terminus-validation-payment-eod-control-chain-31260035556-1`, digest `sha256:583337670bd33fbce706f848bd10004907ab77843464c6337e0cbd06ade9ee66` |
| Task Architect | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/task-architect.json` |
| Verifier Engineer | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/verifier-engineer.json` |
| Originality & Authenticity | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/originality.json` |
| Difficulty design review | PASS_PRE_TRIAL | `.terminus/reviews/payment-eod-control-chain/84d4436f/difficulty-design.json`; final empirical tier not measured |
| Compliance pre-review | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/compliance.json` |
| Instruction Reviewer | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/instruction.json` |
| Documentation Reviewer | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/documentation.json` |
| Comprehensive Reviewer | APPROVE | `.terminus/reviews/payment-eod-control-chain/84d4436f/comprehensive-checklist.json`; 61/61 criteria, 100% coverage, 0 failures |
| Disagreement / omission scan | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/disagreement-scan.json`; no material conflicts; no adjudication required |
| Pre-LLMaJ aggregate | PASS | `.terminus/reviews/payment-eod-control-chain/84d4436f/pre-llmaj-aggregate.json` |
| Reusable STB AI credential | BLOCKED | `STB_AI_API_KEY` / `STB_AI_CONFIG_B64` absent; automatic refresh remains disabled |
| Harbor LLMaJ | NOT_RUN | now eligible by Pre-LLMaJ ordering, but model credential is intentionally unavailable; do not refresh automatically |
| GPT-5.5 difficulty ×5 | NOT_RUN | must remain after Harbor LLMaJ |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | must remain after Harbor LLMaJ |
| Combined difficulty ×10 | NOT_RUN | final empirical tier pending |
| Trial Analysis | NOT_RUN | no model trials yet |
| Final Compliance | PENDING | after model-backed gates |
| Final Human Quality | PENDING | after model-backed gates |
| Final package | PENDING | |

## Oracle authoring failure resolution

The rebuilt Oracle failure series is resolved. The first common runtime defect was the lifecycle boundary after financial reconciliation: a cycle with `reconciliation_status=BALANCED` but incomplete close prerequisites was being treated inconsistently instead of persisting the durable intermediate state required by the close contract.

The reference solution now applies the invariant coherently across the solution-applied runtime:

- `PAYSTATE` returns `RECONCILED` for balanced work whose close decision is not complete;
- controller/close logic persists `state=RECONCILED` and `completion_status=WAITING` while withholding authorization;
- schema guards allow BALANCED -> RECONCILED/WAITING and require a completed balanced cycle before authorization;
- completed work remains idempotent.

Relevant lifecycle repair commits include `e06742eb5afda8ff0194b243ac6a431125a98e11`, `0523ee22a9e45112f8bb4816ca5f1a211c176699`, and `64e8a750fa9e9c973b8e1ee260791a0ecf73a9de`. A later narrow Oracle fix preserves the clearing publication interface for a balanced cycle with zero clearing rows.

No F2P assertion was weakened to obtain Oracle reward 1 or NOP reward 0. The final verifier classification work separated stable starter behavior from close-lifecycle behavior:

- reviewer coverage added focused cases for current-cycle history/restart identity, inconsistent resumed posting/clearing state, cross-cycle replay, blocked payer behavior and stable publication interfaces;
- the stable publication P2P checks customer/clearing CSV shapes on an external route;
- close authorization remains graded by the existing close/idempotency F2P cases, including delivery/report/archive prerequisites and completed rerun behavior;
- current NOP confirms exactly `30 failed, 7 passed`.

## Structural Pre-LLMaJ corrections already applied

These were narrow compliance/reviewer corrections, not task redesign:

- `task.toml` Edition 3 metadata placement was corrected so category/subcategory/tags/languages/difficulty/expert estimate/artifacts are top-level while author/explanations remain under `[metadata]`.
- `instruction.md` names tested solver-visible runtime anchors: `/app/eod/cobol/`, `/app/eod/bin/run_eod.sh`, `/app/eod/sql/schema.sql`, the three operational docs, database and official output paths.
- verifier execution runs the complete `/tests` directory and includes `test_regressions.py`.
- temporary one-use maintenance scripts/workflow hooks used during reviewer coverage work were removed after their intended changes were applied.

## Latest applicable CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31260035556`
- Run number: `150`
- Validate job ID: `93109350869`
- Checkout: PR merge ref `20b2da2438865bffb9b9c0c9dbbfb9c75edbb00a`, merging PR head `4dd807e64ec82cbda09c3717001ccb5c1ae78e74` into task commit `84d4436f027f1ba1dd6ac909f31aae3aaafe9554`
- Oracle: direct Harbor utility agent, verifier collected 37 tests and all 37 passed; reward `1`.
- NOP: direct Harbor utility agent, verifier collected 37 tests; 30 failed and all seven P2P tests passed; reward `0`.
- Evidence artifact: `9022556589`, digest `sha256:583337670bd33fbce706f848bd10004907ab77843464c6337e0cbd06ade9ee66`.
- Workflow overall conclusion is failure only because reusable AI credential preparation fails before Harbor LLMaJ. Harbor LLMaJ is skipped.
- `stb keys refresh` was not run. Automatic refresh is disabled.

Only `.terminus/reviews/**` and this durable session checkpoint changed after the frozen task commit. Those control-plane files do not alter solver-visible task, solution, environment, verifier or metadata behavior, so run #150 remains the applicable Oracle/NOP evidence for task commit `84d4436f...`.

## Pre-LLMaJ review result

Frozen review directory: `.terminus/reviews/payment-eod-control-chain/84d4436f/`

All seven mandatory specialist roles are PASS with sufficient evidence and at least medium confidence. The Comprehensive Reviewer independently records `APPROVE` with `CHECKLIST_COVERAGE: 100%`: 61 total criteria, 40 PASS, 21 structurally/pre-trial NOT_APPLICABLE, 0 FAIL, 0 INSUFFICIENT_EVIDENCE and 0 unresolved POLICY_CONFLICT.

The Stage E disagreement/omission scan found no material contradiction between specialists and comprehensive review, so no adjudication was required. The Pre-LLMaJ aggregate is therefore `PASS`.

Non-blocking deferred evidence:

- final empirical difficulty and trial-analysis rows require the later official combined GPT-5.5 ×5 plus Claude Opus 4.8 ×5 runs;
- no platform-generated test-quality flag bundle is available yet; any future flags must be adjudicated before final acceptance;
- public reviewer-checklist freshness remains `UNVERIFIED`; current repository rules resolved the known metadata, rubric and combined-10-trial interpretation conflicts.

## Current task contract anchors

- Database restart authority: `/app/eod/state/payment_eod.db`
- COBOL programs/interfaces: `/app/eod/cobol/`
- Batch runner: `/app/eod/bin/run_eod.sh`
- Database schema: `/app/eod/sql/schema.sql`
- Solver-facing restart notes: `/app/eod/docs/restart-operations.txt`
- COBOL/file interface notes: `/app/eod/docs/interface-notes.txt`
- Finance reconciliation/close contract: `/app/eod/docs/reconciliation-close.txt`
- Required reconciliation output: `/app/eod/out/reconciliation.json`
- Gated official publications: `/app/eod/out/customer_response.csv`, `/app/eod/out/clearing_submission.csv`
- Close authorization: `/app/eod/out/success_authorization.json`

## Credential architecture

Oracle/NOP use the direct Harbor utility-agent path and do not need an LLM credential. That deterministic authoring gate is complete for the frozen task version.

Model-backed Harbor LLMaJ/difficulty require a reusable STB AI credential. Preferred path remains GitHub Secret `STB_AI_API_KEY`; `STB_AI_CONFIG_B64` is the alternate restored-config path. `STB_ALLOW_KEY_REFRESH` is an emergency fallback only and remains disabled by default.

Do not call `stb keys refresh` as a routine CI action.

## Review freeze boundary

The active semantic-review freeze boundary is task commit `84d4436f027f1ba1dd6ac909f31aae3aaafe9554`, with deterministic evidence from run #150 / artifact `9022556589` and review reports under `.terminus/reviews/payment-eod-control-chain/84d4436f/`.

Any subsequent change to `instruction.md`, `task.toml`, `environment/**`, `solution/**`, `tests/**`, or solver-facing documentation invalidates the affected review dimensions according to `.terminus/agents/PROTOCOL.md`; task/solution/verifier changes may require Oracle/NOP revalidation.

Control-plane-only review/session files do not invalidate the frozen task evidence.

## Next action

1. Do not rerun Oracle/NOP unless a task-relevant file changes.
2. Harbor LLMaJ is the next stage by ordering, but run it only when explicitly resumed with a reusable STB AI credential. Do not refresh AI keys automatically just to enter this gate.
3. After Harbor LLMaJ passes, run the official model difficulty suites in the required order/policy and evaluate the combined 10-run mean plus per-test solvability.
4. Then continue trial analysis, final compliance/human-quality review and packaging.

## Circuit breakers

- Oracle/NOP authoring blocker: `RESOLVED` by run #150 with 37/37 Oracle and exact 30-F2P/7-P2P NOP behavior.
- Pre-LLMaJ blocker: `RESOLVED`; aggregate `PASS` for task commit `84d4436f...`.
- AI refresh circuit breaker: `ACTIVE` for model-backed Harbor operations. Do not refresh automatically.

## Do not retry blindly

- Do not redesign the task from scratch.
- Do not weaken behavioral F2P tests to change gate outcomes.
- Do not force stable P2P behavior to fail NOP.
- Do not rerun Harbor/model gates without reusable credentials.
- Do not refresh AI keys routinely.

## Resume rule

A new controller must load current repository policies, this checkpoint, the frozen review directory, current task files, PR #2 and the newest applicable Actions/Harbor evidence. Repository/current CI evidence always overrides this checkpoint if it becomes stale.
