# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ_PASS`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2` (validation trigger only; do not merge)
- Frozen task/solution commit on `main`: `ff7394ff7bd05a5c851cd1a6a1f62e175c2cd011`
- Applicable validation merge ref: `ec40c51acba50453b34fc2bb949ef138f6744fd0`
- Applicable PR head: `1475e12d541ba8051d59236b563c10803f22236c`
- Agent-system policy: `2.2`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.0`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `UNVERIFIED` until final acceptance refresh

## Current large-system profile

Creator Complexity Gate run `31260792023` (#34), job `93111156631`, on merge ref `ec40c51acba50453b34fc2bb949ef138f6744fd0` reports:

- substantive solver-visible LOC: `3080`
- defect manifestations: `29`
- root-cause clusters: `6`
- interrelated manifestations: `29`
- causal edges: `27`
- verifier tests: `37`
- F2P: `30`
- P2P: `7`
- unclassified: `0`

The current starter is the organic rewrite: previously synthetic/no-op control defects were replaced with plausible but incomplete legacy checks while preserving the same external contract and 29-manifestation causal topology. Private design wording for the affected reconciliation metrics has been synchronized to this starter.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | run `31260792023` (#34), job `93111156631`; 3080 LOC / 29 defects / 6 roots / 37 tests / 30 F2P / 7 P2P |
| Preflight/static | PASS | Terminus CI run `31260792025` (#159), merge ref `ec40c51...` |
| Ruff verifier | PASS | run `31260792025` (#159) |
| STB/Docker setup | PASS | run `31260792025` (#159); direct Harbor utility-agent path |
| Oracle = 1 | PASS | run `31260792025` (#159); 37/37 pytest PASS in 73.60s; reward `1` |
| NOP = 0 | PASS | run `31260792025` (#159); 30 F2P fail + 7 P2P pass in 63.80s; reward `0` |
| Validation evidence artifact | PASS | artifact `9022762311`, digest `sha256:d1e684b622607bae49044fc5023f7aa987fdea360ccd5eb489b66e5e79f1eca5` |
| Task Architect | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/task-architect.json` |
| Verifier Engineer | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/verifier-engineer.json` |
| Originality & Authenticity | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/originality.json` |
| Difficulty design review | PASS_PRE_TRIAL | `.terminus/reviews/payment-eod-control-chain/ff7394ff/difficulty-design.json`; final empirical tier not measured |
| Compliance pre-review | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/compliance.json` |
| Instruction Reviewer | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/instruction.json` |
| Documentation Reviewer | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/documentation.json` |
| Comprehensive Reviewer | APPROVE | `.terminus/reviews/payment-eod-control-chain/ff7394ff/comprehensive-checklist.json`; 61/61 criteria, 100% coverage, 0 failures |
| Disagreement / omission scan | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/disagreement-scan.json`; no material conflict or omission |
| Pre-LLMaJ aggregate | PASS | `.terminus/reviews/payment-eod-control-chain/ff7394ff/pre-llmaj-aggregate.json` |
| Reusable STB AI credential | BLOCKED | `STB_AI_API_KEY` / `STB_AI_CONFIG_B64` absent; automatic refresh remains disabled |
| Harbor LLMaJ | NOT_RUN | next ordered model-backed gate; do not refresh AI keys automatically |
| GPT-5.5 difficulty ×5 | NOT_RUN | only after Harbor LLMaJ |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | only after Harbor LLMaJ |
| Combined difficulty ×10 | NOT_RUN | final empirical tier pending |
| Trial Analysis | NOT_RUN | no model trials yet |
| Final Compliance | PENDING | after model-backed gates |
| Final Human Quality | PENDING | after model-backed gates |
| Final package | PENDING | |

## Oracle failure resolution history

The first common Oracle failure in the rebuilt large task was the lifecycle boundary after financial reconciliation: a cycle with `reconciliation_status=BALANCED` but incomplete close prerequisites was not consistently represented as durable intermediate `RECONCILED/WAITING` state.

The reference solution repairs that invariant across COBOL/controller/close/schema boundaries:

- `PAYSTATE` returns `RECONCILED` for balanced work whose close decision is not complete;
- controller/close logic persists `state=RECONCILED` and `completion_status=WAITING` while withholding authorization;
- schema guards permit BALANCED -> RECONCILED/WAITING and require completed balanced state before authorization;
- completed reruns remain idempotent.

The repair series also handled the empty clearing-publication interface and the final verifier P2P/F2P classification without weakening any unique F2P requirement.

After that deterministic state became green, the solver-visible starter was made more organic. Shell controls that had explicit artificial no-op behavior were replaced with plausible incomplete legacy checks in `control.sh`, `restart.sh`, `reconcile.sh`, `operations.sh` and `lifecycle.sh`. The current Oracle was correspondingly adapted rather than reverting the starter:

- `solution/solve.sh` builds the legacy aggregate patch, filters the organically rewritten files through `solution/filter_repair_patch.py`, applies the remaining patch, then applies direct runtime/schema repairs;
- `solution/apply_runtime_fixes.py` repairs the organic partial checks directly, including full integrity, restart consistency, cycle-scoped reconciliation metrics and held/publication/close behavior;
- no network fetch, verifier access or reward shortcut is used.

The current task/solution boundary is therefore `ff7394ff...`, not the earlier `84d4436f...` freeze.

## Current Oracle/NOP evidence

Workflow: `Terminus Edition 3 CI`

- Run ID: `31260792025`
- Run number: `159`
- Validate job ID: `93111168227`
- PR head: `1475e12d541ba8051d59236b563c10803f22236c`
- Merge ref: `ec40c51acba50453b34fc2bb949ef138f6744fd0`, merging the trigger-only branch into `main` task/solution commit `ff7394ff7bd05a5c851cd1a6a1f62e175c2cd011`
- Oracle: direct Harbor utility agent; verifier collected 37 tests and all 37 passed in 73.60s; reward `1`.
- NOP: direct Harbor utility agent; verifier collected 37 tests; exactly 30 F2P tests failed and all seven P2P tests passed in 63.80s; reward `0`.
- Artifact: `9022762311`, `terminus-validation-payment-eod-control-chain-31260792025-1`, digest `sha256:d1e684b622607bae49044fc5023f7aa987fdea360ccd5eb489b66e5e79f1eca5`.
- Workflow overall conclusion is failure only because reusable AI credential preparation fails before Harbor LLMaJ; Harbor LLMaJ is skipped.
- `stb keys refresh` was not run. Automatic refresh is disabled.

Artifact inspection explicitly confirms the seven NOP passes are the seven declared P2P cases:

- resume internal preserves the existing posting without reapplying balances;
- PAYGUARD consistent values;
- accepted history remains accepted;
- rejected history remains rejected;
- prior-cycle accepted source is suppressed as replay;
- blocked payer remains rejected without financial effect;
- balanced external response/clearing CSV publication retains the documented shape.

All other 30 named tests fail the organic starter and pass Oracle.

## Structural/reviewer corrections already applied

These are narrow governance/coverage fixes, not a task redesign:

- `task.toml` required Edition 3 fields are top-level; author/explanation fields remain under `[metadata]`.
- `instruction.md` names all tested solver-visible runtime anchors while staying concise and non-prescriptive.
- verifier executes the complete `/tests` directory and includes the six focused reviewer regressions.
- final classification is 30 F2P / 7 P2P, empirically verified in run #159.
- private design descriptions D21-D23 now describe incomplete legacy metrics rather than the superseded synthetic “forced to zero” baseline.
- temporary maintenance workflows/helpers were removed after use.

## Pre-LLMaJ review result

Current review directory: `.terminus/reviews/payment-eod-control-chain/ff7394ff/`

All seven mandatory current-version specialist roles are PASS with sufficient evidence and at least medium confidence. The Comprehensive Reviewer records `APPROVE` with `CHECKLIST_COVERAGE: 100%`: 61 total criteria, 40 PASS, 21 structurally/pre-trial NOT_APPLICABLE, 0 FAIL, 0 INSUFFICIENT_EVIDENCE and 0 unresolved POLICY_CONFLICT.

The disagreement/omission scan found no material contradiction or omission, so no adjudication was required. The current Pre-LLMaJ aggregate is `PASS`.

Non-blocking deferred evidence:

- final empirical difficulty/trial-analysis rows require the later official GPT-5.5 ×5 plus Claude Opus 4.8 ×5 runs;
- no platform-generated test-quality flag bundle is currently available; future flags must be adjudicated before final acceptance;
- reviewer-checklist freshness remains `UNVERIFIED`; current repository rules resolved known metadata/rubric/combined-trial conflicts;
- a fresh public originality search during the current review returned a 503 service error, so the prior public comparison was reused because solver-facing framing did not change.

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

Oracle/NOP use the direct Harbor utility-agent path and do not need an LLM credential. That deterministic authoring gate is complete for the current organic-starter version.

Model-backed Harbor LLMaJ/difficulty require a reusable STB AI credential. Preferred path is GitHub Secret `STB_AI_API_KEY`; `STB_AI_CONFIG_B64` is the alternate restored-config path. `STB_ALLOW_KEY_REFRESH` is emergency fallback only and remains disabled by default.

Do not call `stb keys refresh` as a routine CI action.

## Review freeze boundary

The active task/solution freeze boundary is `ff7394ff7bd05a5c851cd1a6a1f62e175c2cd011`, with deterministic evidence from run #159 / artifact `9022762311` and current review reports under `.terminus/reviews/payment-eod-control-chain/ff7394ff/`.

Control-plane-only changes under `.terminus/designs/**`, `.terminus/reviews/**` and `.terminus/sessions/**` after `ff7394ff...` do not alter the solver-visible starter, reference solution or verifier. Any later change to `instruction.md`, `task.toml`, `environment/**`, `solution/**`, `tests/**`, or solver-facing documentation invalidates the affected gates according to `.terminus/agents/PROTOCOL.md` and may require Oracle/NOP revalidation.

## Next action

1. Do not rerun Oracle/NOP unless a task-relevant file changes.
2. Harbor LLMaJ is the next stage by ordering, but run it only when explicitly resumed with a reusable STB AI credential. Do not refresh AI keys automatically merely to enter this gate.
3. After Harbor LLMaJ passes, run the official model difficulty suites and evaluate the combined 10-run mean plus per-test solvability.
4. Then continue trial analysis, final compliance/human-quality review and packaging.

## Circuit breakers

- Oracle/NOP authoring blocker: `RESOLVED` by run #159 on the organic starter: Oracle 37/37, NOP exact 30-F2P/7-P2P behavior.
- Pre-LLMaJ blocker: `RESOLVED`; current aggregate `PASS` for task/solution commit `ff7394ff...`.
- AI refresh circuit breaker: `ACTIVE` for model-backed Harbor operations. Do not refresh automatically.

## Do not retry blindly

- Do not redesign the task from scratch.
- Do not weaken behavioral F2P tests to change gate outcomes.
- Do not reintroduce synthetic no-op starter controls.
- Do not force stable P2P behavior to fail NOP.
- Do not run Harbor/model gates without reusable credentials.
- Do not refresh AI keys routinely.

## Resume rule

A new controller must load current repository policies, this checkpoint, current design/test map, the `ff7394ff` review directory, current task files, PR #2 and the newest applicable Actions/Harbor evidence. Repository/current CI evidence always overrides this checkpoint if it becomes stale.
