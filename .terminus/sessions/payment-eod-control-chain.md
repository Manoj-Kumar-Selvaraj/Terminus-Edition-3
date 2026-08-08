# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `main`
- Pull request: `#6` (merged production-authenticity hardening)
- Current task commit: `eb78d72a8920348ff950a1e811e6fda773d046e5`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Current task profile

The merged task presents the restart problem as a solver-visible production EOD incident rather than a benchmark reproduction. Evidence includes archived failed-run/restart logs, a shift handoff, stale inherited official outputs, a deterministic production-scale database, and substantial COBOL decision programs.

Strict complexity remains coupled rather than padded: 29 defect manifestations across six root-cause clusters, all 29 participating in the causal graph, 27 causal edges / six cross-cluster pairs, and 37 verifier cases split 30 F2P + 7 P2P. Solver-visible implementation is about 4,092 substantive LOC.

Production-authenticity evidence proves 15,012 primary payment records / 135,637 total database rows, 181 cycles, 2,500 payer identities, 15,012 distinct amounts, seven purposes, three currencies, two route variants and three account statuses. The 14 COBOL programs contain substantive parsing, validation, classification and decision flow rather than one-condition micro-program logic.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Production Authenticity Gate | PASS | PR #6 run `31271746652` (#8), job `93138785248`; 7 regression tests PASS; 15,012 payments / 135,637 DB rows / 14 substantive COBOL programs / 3 incident evidence artifacts |
| Creator Complexity Gate | PASS | PR #6 run `31271746662` (#53), job `93138785176`; strict profile, ~4092 substantive LOC / 29 defects / 29 interrelated / 30 F2P / 7 P2P |
| Preflight/static | PASS | PR #6 run `31271746650` (#181), job `93138826901` |
| Ruff verifier | PASS | PR #6 run `31271746650` (#181), job `93138826901` |
| STB auth/AI credentials | BLOCKED | reusable model credential not configured; automatic refresh disabled |
| Oracle = 1 | PASS | PR #6 run `31271746650` (#181), artifact `9025864648`, 37/37 PASS, reward 1 |
| NOP = 0 | PASS | PR #6 run `31271746650` (#181), artifact `9025864648`, all 30 F2P fail + all 7 P2P pass, reward 0 |
| Pre-LLMaJ specialist panel | PENDING | fresh packet queue exists for task commit `eb78d72a`; no review result is promoted until independent reviewer runs finish |
| Task Architect | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-task-architect-8dc0fa4d15.packet.json` |
| Verifier Engineer | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-verifier-engineer-e4b6e3478c.packet.json` |
| Originality & Authenticity | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-originality-a79caa0a38.packet.json` |
| Difficulty design | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-difficulty-design-e84f87464a.packet.json` |
| Compliance pre-review | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-compliance-126981195d.packet.json` |
| Instruction Reviewer | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-instruction-b6eca1dca6.packet.json` |
| Documentation Reviewer | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-documentation-0fc71f6ce8.packet.json` |
| Comprehensive Reviewer | PENDING | `.terminus/reviews/payment-eod-control-chain/eb78d72a/payment-eod-control-chain-eb78d72a-comprehensive-checklist-636231e726.packet.json` |
| Pre-LLMaJ aggregate | PENDING | waiting for frozen independent specialist + Comprehensive results |
| Harbor LLMaJ | NOT_RUN | requires fresh Pre-LLMaJ PASS and reusable model credential |
| Difficulty trials | NOT_RUN | GPT-5.5 ×5 + Claude Opus 4.8 ×5 after Harbor LLMaJ |
| GPT-5.5 difficulty ×5 | NOT_RUN | diagnostic half |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | diagnostic half |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | combined 10 pending |
| Trial Analysis | NOT_RUN | no official model trials for this task version |
| Final Compliance | PENDING | after model-backed evaluation |
| Final Human Quality | PENDING | after model-backed evaluation |
| Final package | PENDING | |

## Fresh production-authenticity review queue

Eight immutable context packets were generated on `main` with `.terminus/new_review_packet.py`. They bind the current task commit to protocol 2.1, prompt policy 2.2, the production-authenticity reviewer contract and role-specific evidence boundaries. The packet generator was removed after use; no temporary workflow remains.

The packet files are contexts only. They do **not** count as reviewer PASS evidence. Each result must be produced in an independent role chat, written to the packet's exact `review_output_path`, and pass `.terminus/validate_review_freshness.py` before the corresponding gate can move from PENDING.

The old ff7394ff review/result set remains immutable historical evidence and is intentionally not reused.

## Production-authenticity controls

The control plane includes `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/validate_runtime_authenticity.py`, regression tests, and a dedicated GitHub Actions gate. Creator policy rejects operational tasks that claim production realism without solver-visible logs/state/handoff evidence, data-backed strict tasks with toy/homogeneous state, and large module counts made from trivial one-condition business logic.

For data-backed `large_system_strict` tasks, the local production profile normally requires 10,000–20,000 deterministic varied primary records. For COBOL-heavy strict tasks, major programs must show substantive reachable parsing, validation, multiple decision branches, procedure paragraphs and real COBOL control structures. Raw LOC does not waive these checks.

The independent reviewer contract is bound to `PRODUCTION_AUTHENTICITY.md`. Reviewer invocation explicitly requires production-evidence, data-scale/variance, business-module-depth and benchmark-framing checks. A future change to this policy changes the role-contract hash and stales prior semantic reviews.

## Current deterministic evidence

- Production Authenticity: PR #6 run `31271746652` (#8), job `93138785248`, PASS.
- Production state metrics: `records=15012`, `database_rows=135637`, `cycles=181`, `payers=2500`, `amounts=15012`, `purposes=7`, `currencies=3`, `routes=2`, `account_statuses=3`.
- COBOL depth: 14 programs; each 74–142 substantive lines with 17–40 processing/decision points; syntax portfolio includes 88-level conditions, COMPUTE, EVALUATE, FUNCTION, PERFORM and UNSTRING.
- Incident evidence: two archived `.log` files plus one shift-handoff `.txt` file.
- Creator Complexity: PR #6 run `31271746662` (#53), job `93138785176`, PASS.
- Terminus Edition 3 deterministic validation: PR #6 run `31271746650` (#181), job `93138826901`.
- Artifact: `9025864648`, digest `sha256:7154ac5a57f8b256120f89d5a35de72dadd67f5516e925736f22866a97cc2ba8`.
- Oracle: `37 passed`, reward `1`.
- NOP: exactly `30 failed, 7 passed`; every `test_f2p_*` failed and every intended `test_p2p_*` passed, reward `0`.
- PR #6 Agent System CI after honest stale-review checkpoint: run `31272058947` (#113), job `93139585604`, PASS including review freshness.
- PR #6 Production Authenticity after checkpoint: run `31272058932` (#9), PASS.
- PR #6 Creator Complexity after checkpoint: run `31272058935` (#54), PASS.
- Overall Edition 3 PR job stops only at the reusable AI-credential gate after Oracle/NOP; no AI-key refresh was consumed.

## Current blocker

`Independent packet-bound semantic reviewers have not yet run for eb78d72a. This chat is the creator/orchestrator context and must not self-certify those roles. After fresh semantic PASS/APPROVE and Pre-LLMaJ aggregate PASS, Harbor/model-backed gates remain separately blocked by the missing reusable model credential.`

## Next action

`Run the eight generated packets in independent reviewer chats. Freeze each result, run review-freshness validation, then disagreement/omission scan and Pre-LLMaJ aggregate. Do not rerun Oracle/NOP unless a task-relevant file changes.`

## Circuit breakers

- Production-authenticity authoring blocker: `RESOLVED`.
- Oracle/NOP authoring blocker: `RESOLVED` by run #181.
- Old semantic evidence: `STALE`; never promote it back to PASS.
- Fresh semantic evidence: `PENDING`; packet existence is not approval.
- AI refresh circuit breaker: `ACTIVE`; never refresh routinely.
- Model-backed evaluation: `BLOCKED` until fresh Pre-LLMaJ PASS and reusable credentials exist.

## Do not retry blindly

- Do not simplify the substantial COBOL programs back into one-condition utilities.
- Do not reduce the production seed to toy fixtures.
- Do not invent unsupported incident backstory merely to sound human.
- Do not weaken F2P behavior to change gate outcomes.
- Do not rerun Oracle/NOP without a task/verifier/solution change.
- Do not self-certify independent reviewer roles from the creator/orchestrator chat.
- Do not run Harbor/model gates until fresh semantic Pre-LLMaJ PASS and reusable credentials exist.

## Resume rule

Verify task commit `eb78d72a8920348ff950a1e811e6fda773d046e5` from Git, load `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, and resume at the eight fresh packet-bound semantic reviews. The deterministic baseline is PR #6 run `31271746650` unless a later task-relevant commit supersedes it.
