# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Current task content commit: `546d56bd6d6145fefda170a8e88ec6a4ae417152`
- Functional task baseline before prose-only rewrite: `f273fede5ae7bc994916e7d32f439eeda09b699c`
- Current CI credential architecture commits: `74d24f5cef38927d514ea19b6f6a7b602c6f2326`, `afffde925ada07fb3bf5a742cdadc02ab4d9835b`
- Agent-system policy: `2.2`
- Specialist prompt policy: `2.2`
- Pre-LLMaJ panel policy: `2.1`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Preflight/static | PASS | run `31243438982` (#81) |
| Ruff verifier | PASS | run `31243438982` (#81), 12 named tests |
| STB/Docker setup | PASS | run `31243438982` (#81), STB 2.4.3 |
| Oracle = 1 | PASS | run `31243438982` (#81), direct Harbor utility agent, no AI key/refresh |
| NOP = 0 | PASS | run `31243438982` (#81), direct Harbor utility agent, no AI key/refresh |
| Reusable STB AI credential | BLOCKED | `STB_AI_API_KEY` / `STB_AI_CONFIG_B64` not configured in GitHub yet; automatic refresh disabled |
| Task Architect | PASS | `pay-eod-f273-task-architect-01`; task topology unchanged |
| Verifier Engineer | PASS | `pay-eod-f273-verifier-01`; verifier/contract unchanged |
| Originality & Authenticity | PASS | `pay-eod-f273-originality-01`; topology unchanged |
| Difficulty design | PASS | `pay-eod-f273-difficulty-design-02`; functional task unchanged |
| Compliance pre-review | PASS | `pay-eod-f273-compliance-01`; task structure/environment unchanged |
| Instruction Reviewer | STALE | final instruction rewritten under human-engineering writing policy 2.2 |
| Documentation Reviewer | PASS | README/explanations unchanged |
| Human Quality | STALE | solver-facing prose changed and writing policy strengthened |
| Comprehensive Reviewer | STALE | instruction criteria must be refreshed under policy 2.2 |
| Pre-LLMaJ aggregate | STALE | prose-related reviews invalidated by instruction rewrite |
| Harbor LLMaJ | NOT_RUN | waiting for reusable STB AI credential; no routine refresh allowed |
| GPT-5.5 difficulty ×5 | NOT_RUN | diagnostic half of final trial set |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | diagnostic half of final trial set |
| Combined difficulty ×10 | NOT_RUN | final tier uses combined 10-run mean |
| Per-test solvability 1/10 | NOT_RUN | every named verifier case must pass at least once across combined 10 |
| Trial Analysis | NOT_RUN | no current trials |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Human-engineering writing revision

Policy 2.2 treats humanization as information selection rather than vocabulary change. Instruction Writer and Instruction Reviewer must apply:

- **Jira/Slack handoff test:** would the text look normal as a real incident/change handoff without benchmark context?
- **Reverse-outline test:** if sentences map neatly to verifier/rubric rows, rewrite around the operational concern.
- **Selectivity rule:** use the instruction for incident, end state and non-obvious constraints; use solver-visible contracts for detailed schemas/protocols.
- **Compressed-rubric rule:** short, polished prose can still be synthetic and must be revised.

## Current instruction

```text
The EOD payment rerun is picking up durable work as if it were new. We’ve seen it after an internal posting and after an external reservation. Fix the restart path under `/app/eod` so it resumes from `/app/eod/state/payment_eod.db` instead of creating another financial effect. Replay control is by an already-accepted source reference; a new source reference is new work even when the rest of the payment looks the same. Keep the existing COBOL decision interfaces in `/app/eod/cobol/paydup.cob` and `/app/eod/cobol/payexec.cob`. The batch runner is `/app/eod/bin/run_eod.sh`, and the schema plus record/output rules are in `/app/eod/sql/schema.sql` and `/app/eod/contracts/eod_contract.md`.

Reconciliation still needs to be written to `/app/eod/out/reconciliation.json` on every run. Only publish `/app/eod/out/customer_response.csv` and `/app/eod/out/clearing_submission.csv` when reconciliation passes, and only write `/app/eod/out/success_authorization.json` after the normal close checks pass. If a rerun is held, don’t leave stale published files behind. Running the same progressed cycle again should leave one financial result, not another.
```

## Credential architecture

STB 2.4.3 performs a global AI-credential precheck even when invoked as `stb harbor run -a oracle` or `-a nop`. Harbor's underlying utility agents themselves do not require an LLM credential.

This was verified by calling Harbor 0.20.0's Typer app directly through the Python environment installed with `snorkelai-stb`:

- direct Harbor Oracle: exit `0`, reward `1`;
- direct Harbor NOP: exit `0`, reward `0`;
- no `stb keys refresh` was executed.

`terminus3.sh` now uses direct Harbor for `oracle`, `nop`, `validate` utility phases and `all-oracle`. Model-backed `check` and difficulty commands remain on STB.

For model-backed operations, the preferred reusable path is GitHub Secret `STB_AI_API_KEY`, installed with the supported `stb keys set` command through `terminus3.sh keys-set --noninteractive`. `STB_AI_CONFIG_B64` remains an alternate restored-config path. `STB_ALLOW_KEY_REFRESH` is an explicit emergency fallback only and is disabled by default.

Do not assume `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `PORTKEY_API_KEY` bypass STB's own AI-key precheck unless future STB evidence proves it.

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31243438982`
- Run number: `81`
- Validate job ID: `93068022716`
- Result: Preflight PASS, Ruff PASS, STB 2.4.3 PASS, Oracle PASS reward 1, NOP PASS reward 0.
- The job stopped at `Prepare reusable AI credentials for Harbor LLMaJ` because no `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is configured.
- No AI credential refresh was requested or consumed.

## Difficulty / solvability checkpoint

- Final policy: GPT-5.5 ×5 + Claude Opus 4.8 ×5; combine all 10.
- Tier mapping: `<20 frontier`, `20–<50 advanced`, `50–<80 core`, `80–<100 base`, `100% reject`.
- Every verifier test must pass at least once across the combined 10 trials.
- Named verifier test cases: `12`.
- Trials completed: `0/10`.

## Circuit breaker

- Old refresh-loop circuit breaker: `RESOLVED FOR ORACLE/NOP` by direct Harbor utility-agent execution.
- AI refresh circuit breaker remains: `ACTIVE` for model-backed LLMaJ/difficulty. Do not call `stb keys refresh` automatically on hosted runners.
- Required next credential action: configure one reusable valid STB AI credential as GitHub Secret `STB_AI_API_KEY`, or restore a known-good STB config with `STB_AI_CONFIG_B64`.

## Next action

1. Cold-review the final instruction under policy 2.2 using Jira/Slack, reverse-outline, selectivity and compressed-rubric checks.
2. Refresh instruction-related Comprehensive Reviewer criteria and Pre-LLMaJ aggregate; preserve unaffected specialist evidence.
3. Configure reusable `STB_AI_API_KEY` without exposing it in chat. Then run Harbor LLMaJ; do not refresh merely because a runner is new.
4. After LLMaJ PASS, run GPT×5 + Claude×5 and perform combined 10-trial difficulty/solvability + trajectory analysis.

## Do not retry blindly

- Do not turn the instruction back into a complete acceptance specification merely to make every test obvious.
- Do not add slang, typos or invented story details as fake humanization.
- Do not weaken or delete requirements; detailed requirements remain discoverable in `/app/eod/contracts/eod_contract.md`.
- Do not invalidate functional reviews for this prose-only change.
- Do not use routine `stb keys refresh` in CI.

## Resume rule

A new controller must load current Edition 3 rules, writing policy 2.2, this checkpoint, task files, PR #2/Actions evidence and frozen review reports. Live repository/CI evidence wins if it differs from this checkpoint.
