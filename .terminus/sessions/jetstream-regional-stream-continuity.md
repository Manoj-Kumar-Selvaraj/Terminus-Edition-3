# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12` (draft quality-interlock validation PR)
- Current task commit: `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Production-authenticity policy: `1.1`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`
- Checklist policy freshness: `CURRENT_LOCAL_SNAPSHOT`

## Current task profile

This is a `large_system_strict` three-domain NATS JetStream continuity task. Two edge domains accept telemetry into durable journals/origin streams; a hub sources both origins, maintains the durable archive index, drives required consumers, and coordinates replay, fencing and retention. The deterministic state contains 12,000 primary telemetry events plus device, generation, archive, effect, checkpoint, replay and retention state.

The Q4 repair preserves the strict 30-case F2P ceiling. The private contract map now contains 25 requirement groups, exactly 30 F2P cases and nine P2P preservation cases. No solver-visible production/runtime/configuration file was changed by the Q4 repair; changes are confined to verifier behavior plus the private test map.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | unchanged: every graded behavior remains discoverable from `instruction.md` plus the referenced continuity contract; Q4 repair did not add prompt-shaped hidden requirements |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | Q4 `REVISE` findings repaired in commits `43d4759c6dcff15922d334ed1c4597d55914ecad` and `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6`; fresh empirical matrix required |
| Q3 Spec Ambiguity Repair | PASS | unchanged: handoff distinguishes controller repair from rewriting captured incident history |
| Q7 Task Format Enforcer | PENDING_FRESH_HEAD_EVIDENCE | verifier files changed; rerun Preflight/Ruff/verifier-image/package checks on task commit `a57ed7e6...` |
| Q5 Oracle & Runtime Repair | NOT_RUN | no production runtime defect identified by Q4; invoke only if fresh Oracle/runtime evidence fails |
| Creator Complexity Gate | PENDING_FRESH_HEAD_EVIDENCE | previous strict PASS belongs to `fc137e82...`; current task commit moved because verifier changed |
| Production Authenticity Gate | PENDING_FRESH_HEAD_EVIDENCE | production files are unchanged but exact task provenance moved; fresh gate required |
| Agent System / review freshness | PENDING_FRESH_HEAD_EVIDENCE | current session now marks old semantic evidence stale; fresh control-plane validation required |
| Preflight/static | PENDING | current task commit `a57ed7e6...` |
| Ruff verifier | PENDING | current task commit `a57ed7e6...` |
| Environment/verifier build | PENDING | current task commit `a57ed7e6...` |
| Oracle = 1 | PENDING | must prove the strengthened 39-test verifier passes the reference solution |
| NOP = 0 | PENDING | must prove exactly the 30 F2P cases fail and all nine P2P cases pass on the inherited starter |
| F2P/P2P empirical matrix | PENDING | target: Oracle 39/39; NOP 30 F2P FAIL + 9 P2P PASS |
| Leakage/package checks | PENDING | rerun after verifier changes |
| FROZEN_CANDIDATE | NOT_REACHED | prior freeze at `fc137e82...` became stale when Q4-required verifier repairs changed the task |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | old result `...spec-test-contract-ad62d62204` is valid historical evidence for task commit `fc137e82...`; verdict REVISE/HIGH/SUFFICIENT; its five findings drove the current repair |
| Q6 Production Logic Auditor | STALE_PASS | old result `...production-logic-823edb7564` was PASS/HIGH/SUFFICIENT for `fc137e82...`; production files are unchanged but exact task-commit binding is stale |
| Quality Interlock | PENDING | cannot pass until fresh packet-bound Q4 and Q6 both PASS on the new frozen task commit |
| Task Architect | PENDING | after Quality Interlock |
| Verifier Engineer | PENDING | after Quality Interlock |
| Originality & Authenticity | PENDING | after Quality Interlock |
| Difficulty design | PENDING | after Quality Interlock |
| Compliance pre-review | PENDING | after Quality Interlock |
| Instruction Reviewer | PENDING | after Quality Interlock |
| Documentation Reviewer | PENDING | after Quality Interlock |
| Comprehensive Reviewer | PENDING | after Stage-B; checklist coverage must be 100% |
| Pre-LLMaJ aggregate | PENDING | requires current specialist + Comprehensive evidence |
| Q8 GPT Perspective | PENDING | isolated diagnostic solve after Pre-LLMaJ PASS; not official model evidence |
| Q8 Claude Perspective | PENDING | isolated diagnostic solve after Pre-LLMaJ PASS; not official model evidence |
| Harbor LLMaJ | PENDING | requires reusable STB AI credential after Pre-LLMaJ/Q8 |
| GPT-5.5 difficulty ×5 | NOT_RUN | official later gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | official later gate |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | every verifier case must pass at least once across combined ten |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | |

## Q4 result and Q2 remediation

The first independent Q4 review was properly packet-bound to task commit `fc137e823b43b939f7005cc598f41fe10e84e3c1` and returned `REVISE`, confidence `HIGH`, evidence `SUFFICIENT`. Q6 independently returned `PASS`, confidence `HIGH`, evidence `SUFFICIENT`, with no production-logic findings.

Q4 identified five verifier-contract issues. The Q2 repair addresses them without expanding the natural instruction or exceeding the 30-F2P ceiling:

1. Removed the unsupported `hub_stream_policy().allow_direct is False` assertion while retaining the contract-backed source-only/no-local-subject topology check.
2. Strengthened the existing final-report F2P to recompute health/reconciliation from copied durable state, compare contract-significant report fields, and verify journal/checkpoint/replay plus captured incident evidence remain intact.
3. Strengthened the existing stale-worker F2P so a stale epoch is exercised through `execute_replay_plan` before any plan-state or publish mutation; added P2P coverage that stale lease release is rejected.
4. Added P2P coverage invoking actual `continuityctl inspect`, `reconcile`, and `verify` against copied durable state and proving protected recovery tables are unchanged while diagnostic reconciliation bookkeeping remains allowed.
5. Removed the vacuous store-level non-overlap P2P and folded real non-overlapping planner behavior into the existing missing-only replay F2P by constructing two disjoint missing ranges through `plan_replay`.

The private map now has `REQ-25` for diagnostic-command non-mutation, 30 F2P tests and nine P2P tests. The temporary GitHub workflow used only to apply the patch was removed. A mechanical indentation defect introduced by that helper was corrected in `test_contract_coverage.py` at commit `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` before accepting any deterministic evidence.

## Historical deterministic evidence

For the prior task commit `fc137e823b43b939f7005cc598f41fe10e84e3c1`, PR #12 validation run `31302792735`, job `93218216997`, artifact `9035022133` proved:

- Oracle 38/38 PASS / reward 1.
- NOP exactly 30 F2P FAIL + 8 P2P PASS / reward 0.
- strict complexity, production authenticity, Preflight, Ruff, environment/verifier build and package isolation passed.

That evidence remains useful historically but is stale for acceptance because verifier behavior changed.

## Historical Q4/Q6 provenance

### Q4 — historical REVISE

- Review ID: `jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204`
- Task commit: `fc137e823b43b939f7005cc598f41fe10e84e3c1`
- Verdict: `REVISE`
- Confidence: `HIGH`
- Evidence: `SUFFICIENT`
- Result: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204.json`

### Q6 — historical PASS, now stale

- Review ID: `jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564`
- Task commit: `fc137e823b43b939f7005cc598f41fe10e84e3c1`
- Verdict: `PASS`
- Confidence: `HIGH`
- Evidence: `SUFFICIENT`
- Result: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564.json`

Neither historical result may satisfy the current Quality Interlock after task commit `a57ed7e6...`.

## Current blocker

`Fresh deterministic validation is required on task commit a57ed7e6afeadaa8228f7c9eda82e09fedb789c6. If Oracle=1, NOP=0, the 30/9 empirical matrix and strict gates pass, return to FROZEN_CANDIDATE and generate new Q4 and Q6 packets. Both independent semantic reviews must then be rerun because the old packet bindings are stale.`

## Root-cause classification

- Owner: `Q2 Verifier Coverage Repairer`
- Classification: `VERIFIER_CONTRACT_COVERAGE`
- Evidence: `Q4 historical REVISE on fc137e82 identified five concrete verifier/spec alignment gaps; no Q6 production-logic defect was found`

## Next action

`Read live PR #12 Actions for task commit a57ed7e6. Require strict complexity/authenticity, Preflight, Ruff, image build, Oracle=1, NOP=0 and empirical Oracle 39/39 / NOP 30-F2P-fail + 9-P2P-pass. Route any runtime failure to Q5 and any verifier-contract defect back to Q2. Only after all deterministic evidence is current may the controller refreeze and generate fresh Q4/Q6 packets.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 from merged PR #11 remain authoritative.
- Keep F2P count at 30; Q4 remediation strengthened/replaced existing F2P coverage rather than adding a 31st case.
- Captured incident state is evidence and must not be rewritten to manufacture a healthy report.
- Current task commit is `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6`.
- Historical Q4 is REVISE; historical Q6 is PASS but stale after the verifier/task commit changed.
- A fresh Q4 and fresh Q6 are required after the next deterministic freeze even though production runtime files did not change.
- Harbor/model credential failure occurs downstream of deterministic validation and does not substitute for the current Oracle/NOP rerun.

## Resume rule

Resolve the task commit from Git and require `a57ed7e6afeadaa8228f7c9eda82e09fedb789c6` unless a newer task-file commit exists. Inspect live PR #12 CI before changing the task. If deterministic validation passes, set `FROZEN_CANDIDATE`, generate new packet-bound Q4/Q6 reviews for the exact task commit, and run those reviews independently in fresh contexts.
