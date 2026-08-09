# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `BLOCKED`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `d7e131f962753acce119afba5f63bd525203d9c7`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | previously completed; latest Q4 reports coverage gaps rather than missing/ambiguous solver contract |
| Q2 Verifier Coverage Repair | REVISE | Q4 result `d28d169713b5df74755c19037f2dfb79b9e9c08a`; findings `Q4-D7E131F9-01`, `-02`, `-03` |
| Q3 Spec Ambiguity Repair | PASS | latest Q4 reports no grading-relevant ambiguity |
| Q7 Task Format Enforcer | PASS | current frozen candidate retained; no task tree change during reviewer-policy migration |
| Creator Complexity Gate | PASS | run `31327893703` |
| Preflight/static | PASS | Edition-3 run `31327893697`, job `93281244115` |
| Ruff verifier | PASS | Edition-3 run `31327893697`, job `93281244115` |
| STB auth/AI credentials | FAIL | reusable-AI credential preparation failed after deterministic validation; not freeze evidence |
| Oracle = 1 | PASS | artifact `9042083147`; exactly 40/40 PASS |
| NOP = 0 | PASS | artifact `9042083147`; exactly 30 F2P FAIL + 10 P2P PASS |
| Q4 Spec-Test Contract Reviewer | STALE | historical old-contract result `.terminus/reviews/jetstream-regional-stream-continuity/d7e131f9/jetstream-regional-stream-continuity-d7e131f9-spec-test-contract-a159fbe550.json`; `REVISE/HIGH/SUFFICIENT`; role policy changed to 1.1 |
| Q6 Production Logic Auditor | STALE | historical old-contract result `.terminus/reviews/jetstream-regional-stream-continuity/d7e131f9/jetstream-regional-stream-continuity-d7e131f9-production-logic-b112d746a8.json`; `PASS/HIGH/SUFFICIENT`; role policy changed to 1.1 and old packet has no scope hash |
| Quality Interlock | BLOCKED | Q4 coverage findings require one consolidated Q2 repair; fresh new-policy Q4/Q6 evidence required afterward |
| Pre-LLMaJ specialist panel | PENDING | not authorized before Quality Interlock PASS |
| Task Architect | PENDING | Stage-B not authorized |
| Verifier Engineer | PENDING | Stage-B not authorized |
| Originality & Authenticity | PENDING | Stage-B not authorized |
| Difficulty design | PENDING | Stage-B not authorized |
| Compliance pre-review | PENDING | Stage-B not authorized |
| Instruction Reviewer | PENDING | Stage-B not authorized |
| Documentation Reviewer | PENDING | Stage-B not authorized |
| Comprehensive Reviewer | PENDING | not authorized |
| Pre-LLMaJ aggregate | PENDING | not authorized |
| Q8 GPT Perspective Simulation | PENDING | not authorized |
| Q8 Claude Perspective Simulation | PENDING | not authorized |
| Harbor LLMaJ | PENDING | not run |
| Difficulty trials | PENDING | not authorized |
| GPT-5.5 difficulty ×5 | PENDING | not authorized |
| Claude Opus 4.8 difficulty ×5 | PENDING | not authorized |
| Combined difficulty ×10 | PENDING | not authorized |
| Per-test solvability 1/10 | PENDING | not authorized |
| Trial Analysis | PENDING | not authorized |
| Final Compliance | PENDING | not authorized |
| Final Human Quality | PENDING | not authorized |
| Final package | PENDING | not authorized |

## Deterministic evidence for current task commit

Task commit `d7e131f962753acce119afba5f63bd525203d9c7` remains the last fully deterministic frozen candidate. No task-directory file was changed by the reviewer-policy migration.

- Edition-3 run `31327893697`, job `93281244115`: Preflight PASS, Ruff PASS, environment/verifier setup PASS, Oracle reward 1, NOP reward 0.
- Artifact `9042083147`, sha256 `c4b39b856b746604c0d121ff72bde3f2f9ed9210be5c3498662395f5aaebccd2`: Oracle exactly 40/40 PASS; NOP exactly 30 F2P FAIL + 10 P2P PASS.
- Creator Complexity run `31327893703`: PASS.
- Production Authenticity run `31327893712`: PASS.
- Agent System/package-isolation run `31327893701`: PASS under the previous control-plane policy; new policy validation must be green before fresh packets are generated.
- Harbor was not run.

## Current blocker

Independent Q4 on `d7e131f9...` returned `REVISE / HIGH / SUFFICIENT` at result commit `d28d169713b5df74755c19037f2dfb79b9e9c08a` with three material verifier-coverage findings:

1. the real replay publication check observes payload `event_id` at the physical west JetStream boundary but not the contractual external `Nats-Msg-Id == event_id` identity;
2. the durable SQLite edge-journal recovery-horizon guarantee is not separately graded from JetStream stream `max_age`;
3. documented `generated_at` fields in `health.json` and `reconciliation.json` are not asserted.

Q6 on the same task commit returned `PASS / HIGH / SUFFICIENT` at `d99e501eed8de2d8c83beef9e2f1c18341eb9c99` with no findings.

Both old packet-bound results are now policy-stale because Q4/Q6 role policy moved from 1.0 to 1.1 and Protocol moved to 2.2. The historical findings/verdicts remain evidence but cannot support a current ready gate.

## Reviewer-control-plane upgrade

The live control plane now requires:

- Q4 to inventory the complete solver-visible requirement set and complete substantive verifier behavior set, complete both mapping directions, walk delegated contracts, F2P/P2P boundaries and stable output interfaces, perform a second omission sweep, and return all material findings in one result;
- explicit Q4 materiality: BLOCKER/HIGH block; MEDIUM blocks only when it changes solver pass/fail, externally observable correctness, safety/durability or a documented stable public interface; LOW is advisory unless an authoritative rule makes it mandatory;
- one normal consolidated repair/refreeze budget after an exhaustive Q4 REVISE; a later finding on unchanged previously-reviewable evidence is `LATENT_REVIEWER_OMISSION` and must be adjudicated before another blind repair cycle;
- Q6 packets/results to carry a conservative production `review_scope_hash` over task `task.toml` plus the full solver-visible `environment/` tree. Once a new-policy Q6 PASS exists, tests/solution/instruction-only changes may preserve it when that scope hash and role contract remain unchanged; production-scope changes still stale Q6.

## Review evidence ledger

| Review | Review ID | Task commit | Protocol | Prompt | Role policy | Result path | Verdict | Confidence | Evidence status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer (historical old contract) | `jetstream-regional-stream-continuity-d7e131f9-spec-test-contract-a159fbe550` | `d7e131f962753acce119afba5f63bd525203d9c7` | 2.1 | 2.2 | 1.0 | `.terminus/reviews/jetstream-regional-stream-continuity/d7e131f9/jetstream-regional-stream-continuity-d7e131f9-spec-test-contract-a159fbe550.json` | REVISE | HIGH | SUFFICIENT |
| Q6 Production Logic Auditor (historical old contract) | `jetstream-regional-stream-continuity-d7e131f9-production-logic-b112d746a8` | `d7e131f962753acce119afba5f63bd525203d9c7` | 2.1 | 2.2 | 1.0 | `.terminus/reviews/jetstream-regional-stream-continuity/d7e131f9/jetstream-regional-stream-continuity-d7e131f9-production-logic-b112d746a8.json` | PASS | HIGH | SUFFICIENT |
| Q4 Spec-Test Contract Reviewer (next) | | next frozen task commit | 2.2 | 2.2 | 1.1 | | PENDING | | |
| Q6 Production Logic Auditor (next) | | next frozen task commit | 2.2 | 2.2 | 1.1 | | PENDING | | scope hash required |

## Circuit breaker / no-drip state

- Status: `TRIPPED` for the old repeated Q4 patch-loop strategy.
- Required strategy: one consolidated Q2 closure for the three known findings, deterministic refreeze, then one exhaustive new-policy Q4 review. Do not return to narrow one-finding-at-a-time repairs.
- The new Protocol-2.2 latent-omission rule applies prospectively to exhaustive Q4 results produced under the new role contract. It is not retroactively asserted for old Q4 1.0 results.

## Next action

Route the three known Q4 findings together to Q2 Verifier Coverage Repair. Preserve exactly 40 tests = 30 F2P + 10 P2P, rerun deterministic validation, and only after a clean refreeze generate fresh Q4 1.1 and Q6 1.1 packets. The fresh Q4 must perform the new exhaustive one-pass audit. The fresh Q6 must record its production `review_scope_hash`; after that, future verifier-only repairs can retain Q6 if the production scope remains byte-identical.

Do not run Stage-B, Harbor or model trials and do not claim `QUALITY_INTERLOCK_PASS` until current-policy evidence validates.
