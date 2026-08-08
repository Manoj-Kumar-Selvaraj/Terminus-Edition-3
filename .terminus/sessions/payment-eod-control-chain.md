# Terminus Task Session

Session schema version: `2.3`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Current task/policy commit: `9bd9ccab518c91b23f6426cf1084377c6f293047`
- Functional task baseline before prose-only rewrite: `f273fede5ae7bc994916e7d32f439eeda09b699c`
- Agent-system policy: `2.2`
- Specialist prompt policy: `2.2`
- Pre-LLMaJ panel policy: `2.1`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Preflight/static | STALE | instruction/policy changed after run #60; functional task files unchanged |
| Ruff verifier | PASS | run `31210474025` (#60), verifier unchanged |
| STB/Docker setup | PASS | run `31210474025` (#60), environment unchanged |
| STB AI credentials | BLOCKED | Portkey project refresh ceiling 20 reached before Oracle |
| Oracle = 1 | INSUFFICIENT_EVIDENCE | current task version has not reached Oracle |
| NOP = 0 | INSUFFICIENT_EVIDENCE | current task version has not reached NOP |
| Task Architect | PASS | `pay-eod-f273-task-architect-01`; task topology unchanged |
| Verifier Engineer | PASS | `pay-eod-f273-verifier-01`; verifier/contract unchanged |
| Originality & Authenticity | PASS | `pay-eod-f273-originality-01`; topology unchanged |
| Difficulty design | PASS | `pay-eod-f273-difficulty-design-02`; functional task unchanged |
| Compliance pre-review | PASS | `pay-eod-f273-compliance-01`; task structure/environment unchanged |
| Instruction Reviewer | STALE | instruction rewritten under human-engineering writing policy 2.2 |
| Documentation Reviewer | PASS | README/explanations unchanged |
| Human Quality | STALE | solver-facing prose changed and writing policy strengthened |
| Comprehensive Reviewer | STALE | instruction criterion statuses must be refreshed under policy 2.2; prior report had 100% coverage/no observed severity failures |
| Pre-LLMaJ aggregate | STALE | prose-related reviews invalidated by instruction rewrite |
| Harbor LLMaJ | NOT_RUN | blocked by local refresh + credentials |
| GPT-5.5 difficulty ×5 | NOT_RUN | diagnostic half of final trial set |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | diagnostic half of final trial set |
| Combined difficulty ×10 | NOT_RUN | final tier uses combined 10-run mean |
| Per-test solvability 1/10 | NOT_RUN | every named verifier case must pass at least once across combined 10 |
| Trial Analysis | NOT_RUN | no current trials |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PENDING | |

## Human-engineering writing revision

The user correctly identified that the previous 157-word instruction was technically sufficient but still artificial. It was a compressed specification: it named several implementation files and then packed the entire output schema/publication contract into one dense second paragraph.

Policy 2.2 now treats humanization as information selection rather than vocabulary change. Instruction Writer and Instruction Reviewer must apply:

- **Jira/Slack handoff test:** would the text look normal as a real incident/change handoff without benchmark context?
- **Reverse-outline test:** if sentences map neatly to verifier/rubric rows, rewrite around the operational concern.
- **Selectivity rule:** use the instruction for incident, end state and non-obvious constraints; use solver-visible contracts for detailed schemas/protocols.
- **Compressed-rubric rule:** short, polished prose can still be synthetic and must be revised.

Current instruction opens from the restart incident, describes the authoritative durable state and replay identity, keeps the existing COBOL interfaces, points to the contract for detailed record/output definitions, and states publication/close behavior in operational terms rather than enumerating JSON fields.

## Current instruction

```text
We hit a restart issue in the EOD payment batch under `/app/eod`. If an earlier attempt has already posted an internal payment or created an external reservation, a rerun can treat that durable state as new work. Fix the batch so it continues from `/app/eod/state/payment_eod.db` instead of applying the same financial effect again. We only consider it the same instruction when that source reference was already accepted; a new source reference is still new work even when the payment details match. Keep the existing decision interfaces in `/app/eod/cobol/paydup.cob` and `/app/eod/cobol/payexec.cob`; the runner is `/app/eod/bin/run_eod.sh`, the schema is `/app/eod/sql/schema.sql`, and the record/output contracts are in `/app/eod/contracts/eod_contract.md`.

Every run should leave `/app/eod/out/reconciliation.json`. `/app/eod/out/customer_response.csv` and `/app/eod/out/clearing_submission.csv` should only be published when reconciliation passes, and `/app/eod/out/success_authorization.json` only after the normal close checks pass. A held rerun must not leave stale published files behind. Once a cycle has progressed, running it again should leave the same financial and close state rather than creating another result.
```

## Latest CI

- Workflow: `Terminus Edition 3 CI`
- Run ID: `31210474025`
- Run number: `60`
- Validate job ID: `92971840881`
- Artifact ID: `9006464682`
- Result before prose rewrite: Preflight PASS, Ruff PASS, STB/Docker PASS, credential refresh FAIL; model-dependent gates skipped.
- Credential error remains `Maximum refresh limit (20) reached` for the Edition-2 Portkey allocation.

## Difficulty / solvability checkpoint

- Final policy: GPT-5.5 ×5 + Claude Opus 4.8 ×5; combine all 10.
- Tier mapping: `<20 frontier`, `20–<50 advanced`, `50–<80 core`, `80–<100 base`, `100% reject`.
- Every verifier test must pass at least once across the combined 10 trials.
- Named verifier test cases: `12`.
- Trials completed: `0/10`.

## Circuit breaker

- Status: `TRIPPED`
- Trigger: hosted-run Portkey refresh limit 20 reached.
- Required strategy change: reusable approved model credentials or a changed eligible project/allocation.
- Do not repeat `stb keys refresh` on the exhausted allocation.

## Next action

1. Cold-review the new instruction under policy 2.2 using the Jira/Slack, reverse-outline, selectivity and compressed-rubric checks.
2. Refresh only instruction-related Comprehensive Reviewer criteria and Pre-LLMaJ aggregate; preserve unaffected specialist evidence.
3. Retrigger cheap preflight/Ruff if useful; do not burn another credential refresh on the known exhausted path.
4. Resolve reusable STB/Portkey credentials, then obtain fresh Oracle/NOP and continue through LLMaJ/difficulty.

## Do not retry blindly

- Do not turn the instruction back into a complete acceptance specification merely to make every test obvious.
- Do not add slang, typos or invented story details as fake humanization.
- Do not weaken or delete requirements; detailed requirements remain discoverable in `/app/eod/contracts/eod_contract.md`.
- Do not invalidate functional reviews for this prose-only change.

## Resume rule

A new controller must load current Edition 3 rules, writing policy 2.2, this checkpoint, task files, PR #2/Actions evidence and frozen review reports. Live repository/CI evidence wins if it differs from this checkpoint.
