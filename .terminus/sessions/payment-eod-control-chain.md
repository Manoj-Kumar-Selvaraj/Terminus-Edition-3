# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/payment-eod-production-hardening`
- Pull request: `#6` (production-authenticity hardening; do not merge until final PR checks are green)
- Current task commit: `f3b49e1a071950406f4d7f4ea39a4f88f5817f34`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Current task profile

The task was materially rebuilt to present a credible production EOD restart incident rather than a benchmark-style reproduction. Solver-visible evidence now includes archived failed-run/restart logs, a shift handoff, stale inherited official outputs, a deterministic production-scale database, and substantial COBOL decision programs.

Strict complexity remains coupled rather than padded: 29 defect manifestations across six root-cause clusters, all 29 participating in the causal graph, 27 causal edges / six cross-cluster pairs, and 37 verifier cases split 30 F2P + 7 P2P. Solver-visible implementation is now about 4,092 substantive LOC.

Production-authenticity evidence on the current task content proves 15,012 primary payment records / 135,637 total database rows, 181 cycles, 2,500 payer identities, 15,012 distinct amounts, seven purposes, three currencies, two route variants and three account statuses. The 14 COBOL programs each contain substantial parsing/validation/classification/decision flow rather than one-condition micro-program logic.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Production Authenticity Gate | PASS | run `31271746652` (#8), job `93138785248`; 7 regression tests PASS; 15,012 payments / 135,637 DB rows / 14 substantive COBOL programs / 3 incident evidence artifacts |
| Creator Complexity Gate | PASS | run `31271746662` (#53), job `93138785176`; strict profile, ~4092 substantive LOC / 29 defects / 29 interrelated / 30 F2P / 7 P2P |
| Preflight/static | PASS | run `31271746650` (#181), job `93138826901` |
| Ruff verifier | PASS | run `31271746650` (#181), job `93138826901` |
| STB auth/AI credentials | BLOCKED | reusable model credential not configured; automatic refresh disabled |
| Oracle = 1 | PASS | run `31271746650` (#181), artifact `9025864648`, 37/37 PASS, reward 1 |
| NOP = 0 | PASS | run `31271746650` (#181), artifact `9025864648`, all 30 F2P fail + all 7 P2P pass, reward 0 |
| Pre-LLMaJ specialist panel | STALE | task and reviewer authenticity contract changed; regenerate fresh packet-bound reviews after production-hardening revision is frozen |
| Task Architect | STALE | historical ff7394ff review predates production-hardening task and authenticity policy |
| Verifier Engineer | STALE | historical ff7394ff review predates current task commit |
| Originality & Authenticity | STALE | historical ff7394ff review predates production evidence/data/COBOL rewrite |
| Difficulty design | STALE | historical ff7394ff review predates current task scale and implementation depth |
| Compliance pre-review | STALE | historical ff7394ff review predates current task/control-plane files |
| Instruction Reviewer | STALE | instruction materially changed to evidence-backed incident handoff and reviewer contract now includes production authenticity |
| Documentation Reviewer | STALE | README materially changed and reviewer contract now includes production authenticity |
| Comprehensive Reviewer | STALE | task and checklist evidence surface changed materially |
| Pre-LLMaJ aggregate | STALE | all controlling semantic inputs are stale |
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

## Production-authenticity controls added

The control plane now includes `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, `.terminus/validate_runtime_authenticity.py`, regression tests, and a dedicated GitHub Actions gate. Creator policy rejects operational tasks that claim production realism without solver-visible logs/state/handoff evidence, data-backed strict tasks with toy/homogeneous state, and large module counts made from trivial one-condition business logic.

For data-backed `large_system_strict` tasks, the local production profile normally requires 10,000–20,000 deterministic varied primary records. For COBOL-heavy strict tasks, major programs must show substantive reachable parsing, validation, multiple decision branches, procedure paragraphs and real COBOL control structures. Raw LOC does not waive these checks.

The independent reviewer contract is also bound to `PRODUCTION_AUTHENTICITY.md`. Reviewer invocation explicitly requires production-evidence, data-scale/variance, business-module-depth and benchmark-framing checks. A future change to this policy changes the role-contract hash and stales prior semantic reviews.

## Current deterministic evidence

- Production Authenticity: run `31271746652` (#8), job `93138785248`, PASS.
- Production state metrics: `records=15012`, `database_rows=135637`, `cycles=181`, `payers=2500`, `amounts=15012`, `purposes=7`, `currencies=3`, `routes=2`, `account_statuses=3`.
- COBOL depth: 14 programs; each 74–142 substantive lines with 17–40 processing/decision points; syntax portfolio includes 88-level conditions, COMPUTE, EVALUATE, FUNCTION, PERFORM and UNSTRING.
- Incident evidence: two archived `.log` files plus one shift-handoff `.txt` file.
- Creator Complexity: run `31271746662` (#53), job `93138785176`, PASS.
- Terminus Edition 3 deterministic validation: run `31271746650` (#181), job `93138826901`.
- Artifact: `9025864648`, digest `sha256:7154ac5a57f8b256120f89d5a35de72dadd67f5516e925736f22866a97cc2ba8`.
- Oracle: `37 passed`, reward `1`.
- NOP: exactly `30 failed, 7 passed`; every `test_f2p_*` failed and every intended `test_p2p_*` passed, reward `0`.
- Overall Edition 3 job stops only at the reusable AI-credential gate before Harbor LLMaJ; no AI-key refresh was consumed.

## Why previous semantic evidence is stale

The solver-visible instruction, README, seed state, incident evidence and all major COBOL decision programs changed. The reference solution also changed. In addition, `PRODUCTION_AUTHENTICITY.md` was added to reviewer role-contract hashing. The old ff7394ff packet/result set therefore cannot support any current semantic PASS even where the underlying conceptual requirement is similar.

Do not rewrite or delete old reports. They remain historical evidence.

## Current blocker

`Deterministic production-hardening is green. PR #6 still needs final control-plane CI/freshness on this checkpoint, then the task should be merged/frozen and a fresh v3 semantic Pre-LLMaJ cycle generated for the resulting task commit. Harbor/model-backed gates remain separately blocked by the missing reusable model credential.`

## Next action

`Confirm PR #6 final Production Authenticity, Creator Complexity and Agent System CI on this session checkpoint. Merge only when the deterministic/control-plane PR checks are clean. After merge, resolve the new main task commit, generate fresh v3 packets under the production-authenticity reviewer contract, rerun the independent Stage-B specialists and cold Comprehensive Reviewer, then rebuild the Pre-LLMaJ aggregate. Do not rerun Oracle/NOP unless a task-relevant file changes.`

## Circuit breakers

- Production-authenticity authoring blocker: `RESOLVED` by current gate.
- Oracle/NOP authoring blocker: `RESOLVED` by run #181.
- Old semantic evidence: `STALE`; never promote it back to PASS.
- AI refresh circuit breaker: `ACTIVE`; never refresh routinely.
- Model-backed evaluation: `BLOCKED` until fresh Pre-LLMaJ PASS and reusable credentials exist.

## Do not retry blindly

- Do not simplify the substantial COBOL programs back into one-condition utilities.
- Do not reduce the production seed to toy fixtures.
- Do not invent unsupported incident backstory merely to sound human.
- Do not weaken F2P behavior to change gate outcomes.
- Do not rerun Oracle/NOP without a task/verifier/solution change.
- Do not run Harbor/model gates until fresh semantic Pre-LLMaJ PASS and reusable credentials exist.

## Resume rule

Verify the current task commit from Git, load `.terminus/agents/PRODUCTION_AUTHENTICITY.md`, inspect PR #6 and current CI, and resume from the first incomplete gate. The deterministic baseline is run `31271746650` unless a later task-relevant commit supersedes it.
