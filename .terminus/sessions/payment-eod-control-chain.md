# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2` (validation trigger only; do not merge)
- Current task content commit on `main`: `4e90ed5082e675bab386ba6dfd7d3cea6d89116b`
- Current validation merge ref: `3cfaf511e1c1df94a1dc623389aca06b0d20b4be`
- Current PR head: `4dafd98f80ddc86dfcbd6b7771850abd32ac345e`
- Agent-system policy: `2.2`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.0`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `UNVERIFIED` until final acceptance refresh

## Current large-system profile

Live Creator Complexity Gate evidence for the current PR merge ref reports:

- substantive solver-visible LOC: `3055`
- defect manifestations: `29`
- root-cause clusters: `6`
- interrelated manifestations: `29`
- causal edges: `27`
- verifier tests: `31`
- F2P: `27`
- P2P: `4`
- unclassified: `0`

The former estimate of roughly 28 F2P + 3 P2P is superseded by the current test-map reclassification. `test_p2p_resume_internal_keeps_the_existing_posting_without_reapplying_balances` is now P2P because the starter already preserves that stable behavior.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | workflow run `31258442436` (#7), job `93105393277`; 3055 LOC / 29 defects / 31 tests |
| Preflight/static | PASS | Terminus CI run `31258442443` (#117), merge ref `3cfaf511...` |
| Ruff verifier | PASS | run `31258442443` (#117) |
| STB/Docker setup | PASS | run `31258442443` (#117), STB `2.4.3`, Harbor `0.20.0` |
| Oracle = 1 | PASS | run `31258442443` (#117), direct Harbor utility-agent path, 31/31 pytest PASS, reward `1.0`, 0 exceptions |
| NOP = 0 | PASS | run `31258442443` (#117), direct Harbor utility-agent path, reward `0.0`, 0 exceptions; 27 F2P fail and 4 P2P pass |
| Validation evidence artifact | PASS | artifact `9022110194`, `terminus-validation-payment-eod-control-chain-31258442443-1`, digest `sha256:3944fc27183ae8a6f5b1ea24f6da386b7e3bc2f7291bc42d889e29b1a4353ff6` |
| Reusable STB AI credential | BLOCKED | `STB_AI_API_KEY` / `STB_AI_CONFIG_B64` absent; automatic refresh remains disabled |
| Task Architect | STALE | prior report was for pre-rebuild task; large-system environment/contract changed |
| Verifier Engineer | STALE | verifier expanded to 31 tests and test map changed |
| Originality & Authenticity | STALE | failure topology/environment changed materially |
| Difficulty design review | STALE | task reasoning topology changed; do not run model difficulty trials yet |
| Compliance pre-review | STALE | environment/task structure changed materially |
| Instruction Reviewer | STALE | rebuilt solver-visible docs/instruction require cold review |
| Documentation Reviewer | STALE | README/explanations changed with rebuilt task |
| Comprehensive Reviewer | STALE | must be rerun after current specialist reviews |
| Pre-LLMaJ aggregate | STALE | all semantic reports must be current for rebuilt task |
| Harbor LLMaJ | NOT_RUN | prohibited until current Pre-LLMaJ PASS; no AI-key refresh |
| GPT-5.5 difficulty ×5 | NOT_RUN | do not run yet |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | do not run yet |
| Combined difficulty ×10 | NOT_RUN | do not run yet |
| Trial Analysis | NOT_RUN | no current model trials |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Oracle authoring failure resolution

The Oracle failure series from the rebuilt task is resolved in current live CI. The common lifecycle defect was that a cycle with `reconciliation_status=BALANCED` but incomplete close prerequisites was not represented consistently as the durable intermediate state required by the solver-visible close contract.

The current reference solution now applies that invariant coherently across the solution-applied runtime:

- `PAYSTATE` returns `RECONCILED` for balanced work whose close decision is not complete;
- the close/controller path persists `state=RECONCILED` and `completion_status=WAITING` while withholding authorization;
- schema guards preserve the BALANCED -> RECONCILED/WAITING transition and require a completed balanced cycle before authorization;
- completed work remains idempotent.

Relevant repair-history commits include `e06742eb5afda8ff0194b243ac6a431125a98e11`, `0523ee22a9e45112f8bb4816ca5f1a211c176699`, and `64e8a750fa9e9c973b8e1ee260791a0ecf73a9de`. The final test reclassification is at `4e90ed5082e675bab386ba6dfd7d3cea6d89116b`.

No test was weakened to obtain Oracle reward 1. The stable resume regression was reclassified rather than forced to fail NOP.

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31258442443`
- Run number: `117`
- Validate job ID: `93105430465`
- Checkout: PR merge ref `3cfaf511e1c1df94a1dc623389aca06b0d20b4be`, merging PR head `4dafd98f...` into current main `4e90ed50...`
- Oracle: direct Harbor utility agent, `1/1 Mean: 1.000`, 0 exceptions; verifier collected 31 tests and all passed.
- NOP: direct Harbor utility agent, `1/1 Mean: 0.000`, 0 exceptions.
- The workflow fails only at reusable AI credential preparation before Harbor LLMaJ because no reusable STB AI credential is configured.
- `stb keys refresh` was not run. Automatic refresh is disabled.

## Current task contract anchors

- Database restart authority: `/app/eod/state/payment_eod.db`
- Solver-facing restart notes: `/app/eod/docs/restart-operations.txt`
- COBOL/file interface notes: `/app/eod/docs/interface-notes.txt`
- Finance reconciliation/close contract: `/app/eod/docs/reconciliation-close.txt`
- Batch runner: `/app/eod/bin/run_eod.sh`
- Required reconciliation output: `/app/eod/out/reconciliation.json`
- Gated official publications: `/app/eod/out/customer_response.csv`, `/app/eod/out/clearing_submission.csv`
- Close authorization: `/app/eod/out/success_authorization.json`

## Credential architecture

Oracle/NOP use the direct Harbor utility-agent path and do not need an LLM credential. Keep that path for deterministic authoring validation.

Model-backed Harbor LLMaJ/difficulty still require a reusable STB AI credential. Preferred path remains GitHub Secret `STB_AI_API_KEY`; `STB_AI_CONFIG_B64` is the alternate restored-config path. `STB_ALLOW_KEY_REFRESH` is an emergency fallback only and remains disabled by default.

Do not call `stb keys refresh` as a routine CI action.

## Current review invalidation

The old frozen semantic reports under the pre-rebuild task commit cannot be preserved as current PASS evidence. The large-system rebuild changed the starter environment, solver-visible contract/docs, solution, verifier topology and test inventory. Per `.terminus/agents/PROTOCOL.md`, all affected Pre-LLMaJ dimensions must be cold-reviewed again for the current task version.

## Next action

1. Resume Pre-LLMaJ Stage B on the current rebuilt task: Task Architect, Verifier Engineer, Originality & Authenticity, Compliance, Instruction, Documentation, and the required pre-trial difficulty-design review. Do not run Harbor/model difficulty trials.
2. Freeze the current specialist reports without exposing verdicts between cold reviewers.
3. Run the independent Comprehensive Reviewer with `CHECKLIST_COVERAGE: 100%`, using current Oracle/NOP/static evidence and no trial evidence.
4. Perform disagreement/omission scan and adjudicate material conflicts if any.
5. Record the Pre-LLMaJ aggregate. Only after aggregate PASS may Harbor LLMaJ be considered, and no AI key refresh should be consumed merely to reach it.

## Circuit breakers

- Oracle/NOP authoring blocker: `RESOLVED` by live run #117.
- AI refresh circuit breaker: `ACTIVE` for model-backed Harbor operations. Do not refresh automatically.
- No Oracle retry is justified while current live evidence remains reward `1` / `0` for the same applicable task version.

## Do not retry blindly

- Do not redesign the task from scratch.
- Do not weaken behavioral tests to change gate outcomes.
- Do not convert current P2P behavior into an artificial F2P failure.
- Do not run Harbor LLMaJ or model difficulty trials before current Pre-LLMaJ review is complete.
- Do not refresh AI keys routinely.

## Resume rule

A new controller must load the current repository rules and reviewer policies, this checkpoint, current task files, PR #2 and the newest Actions/Harbor evidence. Repository/current CI evidence always overrides this checkpoint if it becomes stale.
