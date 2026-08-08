# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2` (validation trigger only; do not merge)
- Current task content commit on `main`: `84d4436f027f1ba1dd6ac909f31aae3aaafe9554`
- Current validation merge ref: `20b2da2438865bffb9b9c0c9dbbfb9c75edbb00a`
- Current PR head: `4dd807e64ec82cbda09c3717001ccb5c1ae78e74`
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

The 30/7 classification is empirically confirmed by the latest NOP artifact: all seven `test_p2p_*` cases pass the starter and all 30 F2P cases fail it.

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
| Reusable STB AI credential | BLOCKED | `STB_AI_API_KEY` / `STB_AI_CONFIG_B64` absent; automatic refresh remains disabled |
| Task Architect | PENDING_COLD_REVIEW | current rebuilt 37-test task |
| Verifier Engineer | PENDING_COLD_REVIEW | current 30 F2P / 7 P2P suite |
| Originality & Authenticity | PENDING_COLD_REVIEW | current large-system failure topology |
| Difficulty design review | PENDING_COLD_REVIEW | design-only review; do not run model difficulty trials |
| Compliance pre-review | PENDING_COLD_REVIEW | current task structure/environment |
| Instruction Reviewer | PENDING_COLD_REVIEW | current concise two-paragraph handoff |
| Documentation Reviewer | PENDING_COLD_REVIEW | current README/explanations |
| Comprehensive Reviewer | PENDING | run only after current specialist reports are frozen |
| Pre-LLMaJ aggregate | PENDING | |
| Harbor LLMaJ | NOT_RUN | prohibited until current Pre-LLMaJ aggregate passes; do not refresh AI keys |
| GPT-5.5 difficulty ×5 | NOT_RUN | do not run yet |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | do not run yet |
| Combined difficulty ×10 | NOT_RUN | do not run yet |
| Trial Analysis | NOT_RUN | no current model trials |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Oracle authoring failure resolution

The rebuilt Oracle failure series is resolved. The first common runtime defect was the lifecycle boundary after financial reconciliation: a cycle with `reconciliation_status=BALANCED` but incomplete close prerequisites was being treated inconsistently instead of persisting the durable intermediate state required by the close contract.

The reference solution now applies the invariant coherently across the solution-applied runtime:

- `PAYSTATE` returns `RECONCILED` for balanced work whose close decision is not complete;
- controller/close logic persists `state=RECONCILED` and `completion_status=WAITING` while withholding authorization;
- schema guards allow BALANCED -> RECONCILED/WAITING and require a completed balanced cycle before authorization;
- completed work remains idempotent.

Relevant lifecycle repair commits include `e06742eb5afda8ff0194b243ac6a431125a98e11`, `0523ee22a9e45112f8bb4816ca5f1a211c176699`, and `64e8a750fa9e9c973b8e1ee260791a0ecf73a9de`. A later narrow Oracle fix at `05a5e5...` preserves the clearing publication interface for a balanced cycle with zero clearing rows.

No F2P assertion was weakened to obtain Oracle reward 1 or NOP reward 0. The final verifier classification work separated stable starter behavior from close-lifecycle behavior:

- six additional reviewer regressions were added for current-cycle history/restart identity, inconsistent resumed posting/clearing state, cross-cycle replay, blocked payer behavior and stable publication interfaces;
- the stable publication P2P checks customer/clearing CSV shapes on an external route;
- close authorization remains graded by the existing close/idempotency F2P cases, including delivery/report/archive prerequisites and completed rerun behavior;
- current NOP confirms exactly `30 failed, 7 passed`.

## Structural Pre-LLMaJ corrections already applied

These were narrow compliance/reviewer corrections, not task redesign:

- `task.toml` Edition 3 metadata placement was corrected so category/subcategory/tags/languages/difficulty/expert estimate are top-level while author/explanations remain under `[metadata]`.
- `instruction.md` now names tested solver-visible runtime anchors: `/app/eod/cobol/`, `/app/eod/bin/run_eod.sh`, `/app/eod/sql/schema.sql`, the three operational docs, database and official output paths.
- verifier execution now runs the complete `/tests` directory and includes `test_regressions.py`.
- temporary one-use maintenance scripts/workflow hooks used during reviewer coverage work were removed after the intended changes were applied.

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31260035556`
- Run number: `150`
- Validate job ID: `93109350869`
- Checkout: PR merge ref `20b2da2438865bffb9b9c0c9dbbfb9c75edbb00a`, merging PR head `4dd807e64ec82cbda09c3717001ccb5c1ae78e74` into main `84d4436f027f1ba1dd6ac909f31aae3aaafe9554`
- Oracle: direct Harbor utility agent, verifier collected 37 tests and all 37 passed; reward `1`.
- NOP: direct Harbor utility agent, verifier collected 37 tests; 30 failed and all 7 P2P tests passed; reward `0`.
- Evidence artifact: `9022556589`, digest `sha256:583337670bd33fbce706f848bd10004907ab77843464c6337e0cbd06ade9ee66`.
- Workflow overall conclusion is failure only because reusable AI credential preparation fails before Harbor LLMaJ. Harbor LLMaJ is skipped.
- `stb keys refresh` was not run. Automatic refresh is disabled.

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

Oracle/NOP use the direct Harbor utility-agent path and do not need an LLM credential. Keep that path for deterministic authoring validation.

Model-backed Harbor LLMaJ/difficulty require a reusable STB AI credential. Preferred path remains GitHub Secret `STB_AI_API_KEY`; `STB_AI_CONFIG_B64` is the alternate restored-config path. `STB_ALLOW_KEY_REFRESH` is an emergency fallback only and remains disabled by default.

Do not call `stb keys refresh` as a routine CI action.

## Current review invalidation and freeze boundary

All semantic reports from the pre-rebuild task are stale. The current cold-review freeze boundary is task commit `84d4436f027f1ba1dd6ac909f31aae3aaafe9554` with deterministic evidence from run #150 / artifact `9022556589`.

Any subsequent change to instruction, environment, solution, tests, task metadata or solver-facing documentation must invalidate the affected review dimensions according to `.terminus/agents/PROTOCOL.md` and may require Oracle/NOP revalidation.

## Next action

1. Execute Pre-LLMaJ Stage B cold reviews on the frozen current task: Task Architect, Verifier Engineer, Originality & Authenticity, pre-trial Difficulty Design, Compliance, Instruction and Documentation.
2. Freeze those reports without feeding verdicts between reviewer roles.
3. Run Comprehensive Reviewer against the complete current task and deterministic evidence with `CHECKLIST_COVERAGE: 100%`; trial-dependent criteria remain `NOT_APPLICABLE_PRE_TRIAL`.
4. Perform disagreement/omission scan and adjudicate material conflicts.
5. Record the Pre-LLMaJ aggregate. Only after aggregate PASS may Harbor LLMaJ be considered; do not consume an AI-key refresh just to reach it.

## Circuit breakers

- Oracle/NOP authoring blocker: `RESOLVED` by run #150 with 37/37 Oracle and exact 30-F2P/7-P2P NOP behavior.
- AI refresh circuit breaker: `ACTIVE` for model-backed Harbor operations. Do not refresh automatically.
- Do not retry Oracle/NOP again unless a task-relevant file changes or current CI evidence becomes superseded.

## Do not retry blindly

- Do not redesign the task from scratch.
- Do not weaken behavioral F2P tests to change gate outcomes.
- Do not force stable P2P behavior to fail NOP.
- Do not run Harbor LLMaJ or model difficulty trials before current Pre-LLMaJ review is complete.
- Do not refresh AI keys routinely.

## Resume rule

A new controller must load current repository policies, this checkpoint, current task files, PR #2 and the newest Actions/Harbor evidence. Repository/current CI evidence always overrides this checkpoint if it becomes stale.
