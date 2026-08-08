# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2` (validation trigger only; do not merge)
- Current task commit: `ff7394ff7bd05a5c851cd1a6a1f62e175c2cd011`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `UNVERIFIED`

## Current task profile

The solver-visible task/solution/verifier tree remains at `ff7394ff...`; control-plane PR #4 does not modify those task files. The private authoring design is explicitly `large_system_strict`, so Creator Complexity must satisfy both the project-owner numeric scale and structural-authenticity checks.

Current strict Creator Complexity evidence is run `31265052075` (#43), job `93121741077`: 3,080 substantive solver-visible LOC, 29 defect manifestations, six root-cause clusters, all 29 manifestations interrelated across 27 causal edges / six cross-cluster pairs, and 37 verifier cases split 30 F2P + 7 P2P. The strict gate passed.

Last task-version Oracle/NOP evidence remains Terminus Edition 3 CI run `31260792025` (#159): Oracle 37/37 with reward 1; NOP 30 F2P failures + 7 P2P passes with reward 0. Artifact `9022762311` records that run. Those results remain applicable because no task/verifier/solution path changed.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | run `31265052075` (#43), job `93121741077`; strict profile 3080 LOC / 29 defects / 29 interrelated / 30 F2P / 7 P2P |
| Preflight/static | PASS | run `31260792025` (#159) |
| Ruff verifier | PASS | run `31260792025` (#159) |
| STB auth/AI credentials | BLOCKED | reusable model credential not configured; automatic refresh disabled |
| Oracle = 1 | PASS | run `31260792025` (#159), artifact `9022762311`, 37/37 pass, reward 1 |
| NOP = 0 | PASS | run `31260792025` (#159), artifact `9022762311`, 30 F2P fail + 7 P2P pass, reward 0 |
| Pre-LLMaJ specialist panel | STALE | legacy schema/protocol review set; must rerun under packet/result v3 |
| Task Architect | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/task-architect.json` |
| Verifier Engineer | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/verifier-engineer.json` |
| Originality & Authenticity | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/originality.json` |
| Difficulty design | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/difficulty-design.json` |
| Compliance pre-review | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/compliance.json` |
| Instruction Reviewer | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/instruction.json` |
| Documentation Reviewer | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/documentation.json` |
| Comprehensive Reviewer | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/comprehensive-checklist.json` |
| Pre-LLMaJ aggregate | STALE | historical `.terminus/reviews/payment-eod-control-chain/ff7394ff/pre-llmaj-aggregate.json` |
| Harbor LLMaJ | NOT_RUN | requires fresh Pre-LLMaJ PASS and reusable model credential |
| Difficulty trials | NOT_RUN | GPT-5.5 ×5 + Claude Opus 4.8 ×5 after Harbor LLMaJ |
| GPT-5.5 difficulty ×5 | NOT_RUN | diagnostic half |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | diagnostic half |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | combined 10 pending |
| Trial Analysis | NOT_RUN | no official model trials yet |
| Final Compliance | PENDING | after model-backed evaluation |
| Final Human Quality | PENDING | after model-backed evaluation |
| Final package | PENDING | |

## Why semantic gates are stale

The old `ff7394ff` specialist reports were produced before protocol 2.1 and review schema v3. The task itself did not move, but the evidence contract did: new ready semantic reviews require a generated context packet, unique review ID, explicit protocol/prompt/role provenance, role-contract hash and packet/result binding. Historical reports remain immutable evidence and are not rewritten into v3.

## Current deterministic evidence

- Creator Complexity run: `31265052075` (#43), job `93121741077`, strict gate PASS.
- Complexity metrics: `substantive_loc=3080`, `defects=29`, `root_causes=6`, `interrelated=29`, `edges=27`, `cross_cluster_pairs=6`, `f2p=30`, `p2p=7`.
- Terminus validation run: `31260792025` (#159).
- Oracle: 37/37 pytest PASS, reward `1`.
- NOP: exactly 30 `test_f2p_*` failures and seven `test_p2p_*` passes, reward `0`.
- Artifact: `9022762311`, digest `sha256:d1e684b622607bae49044fc5023f7aa987fdea360ccd5eb489b66e5e79f1eca5`.
- Oracle/NOP use the direct Harbor utility-agent path and do not consume AI key refreshes.
- Control-plane PR #4 final validation before this checkpoint: Agent System CI run `31265052074` (#88) PASS with 45 regression tests, Ruff PASS, agent-system validator PASS, freshness PASS with zero warnings; Creator Complexity run `31265052075` (#43) PASS; Terminus Edition 3 CI run `31265052077` (#166) PASS.

## Difficulty policy

Final difficulty/solvability uses GPT-5.5 ×5 plus Claude Opus 4.8 ×5 combined. A five-run suite is diagnostic only. Every verifier case must pass at least once somewhere across the combined 10. The old 5-vs-10 conflict is resolved and must not be reopened merely because each model contributes five trials.

## Credential architecture

Oracle/NOP are key-free utility-agent gates. Model-backed Harbor LLMaJ/difficulty uses reusable STB credentials when configured. `stb keys refresh` is emergency fallback only and must not be called routinely.

## Current blocker

`Control-plane PR #4 is implementation-complete and CI-green; it must be merged before the current task's semantic reviewers are regenerated under the authoritative v3 packet/result protocol.`

## Root-cause classification

- Owner: `CI Orchestrator / Submission Controller`
- Classification: `review_disagreement / evidence-provenance migration`
- Evidence: `PR #4; Agent System CI #88; Creator Complexity #43; protocol 2.1; context/review schema v3`

## Next action

`Merge PR #4 when approved. Then generate fresh v3 packets for the current ff7394ff task commit and rerun only the stale semantic Pre-LLMaJ roles; do not rerun Oracle/NOP unless a task-relevant file changes.`

## Review evidence ledger

All stored `ff7394ff` semantic reports are historical/STALE under protocol 2.1. No current v3 review has been generated yet.

## Circuit breakers

- Oracle/NOP authoring blocker: `RESOLVED` by run #159.
- AI refresh circuit breaker: `ACTIVE`; do not refresh automatically.
- Control-plane provenance migration: `RESOLVED`; PR #4 final control-plane CI is green.

## Do not retry blindly

- Do not redesign the COBOL task from scratch.
- Do not weaken F2P behavior to change gate outcomes.
- Do not rerun Oracle/NOP without a task/verifier/solution change.
- Do not promote legacy semantic reviews back to PASS.
- Do not run Harbor/model gates until fresh Pre-LLMaJ PASS and reusable credentials exist.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, verifies the current task commit from Git, loads current protocol/schema/packet rules, inspects PR #4 and current CI, and resumes from the first stale or incomplete gate.
