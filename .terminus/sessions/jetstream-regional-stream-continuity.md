# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12` (draft quality-interlock validation PR)
- Current task commit: `fc137e823b43b939f7005cc598f41fe10e84e3c1`
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

The current strict complexity evidence measures 5,488 substantive solver-visible runtime/configuration LOC, 26 manifestations across seven root-cause clusters, 28 causal edges, 11 cross-cluster pairs, 11 affected components, 24 mapped requirement groups, exactly 30 F2P tests and eight P2P tests.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | instruction plus referenced continuity contract cover every currently graded behavior without hidden-test-shaped expansion |
| Q2 Verifier Coverage Repair | PASS | PR #12 artifact `9035022133`: Oracle 38/38 PASS; NOP exactly 30 F2P FAIL + 8 P2P PASS |
| Q3 Spec Ambiguity Repair | PASS | handoff distinguishes control-plane repair from rewriting incident history; detailed contract narrows grading-relevant semantics |
| Q7 Task Format Enforcer | PASS | run `31302792735`, job `93218216997`: Preflight, Ruff and Docker/STB install PASS; verifier image includes both test modules |
| Q5 Oracle & Runtime Repair | NOT_RUN | not triggered because current Oracle/runtime execution is green |
| Creator Complexity Gate | PASS | run `31302792708`, job `93218169623`: strict PASS; `substantive_loc=5488`, `tests_total=38`, `f2p=30`, `p2p=8`, `requirements=24` |
| Production Authenticity Gate | PASS | run `31302792706`, job `93218169731` PASS on current task version |
| Agent System / review freshness | PASS | run `31302792712`, job `93218169903`: control-plane regressions, structure, freshness and package isolation PASS |
| Preflight/static | PASS | run `31302792735`, job `93218216997` |
| Ruff verifier | PASS | run `31302792735`, job `93218216997` |
| Environment/verifier build | PASS | run `31302792735`, job `93218216997` |
| Oracle = 1 | PASS | run `31302792735`, job `93218216997`; Oracle mean `1.000`; verifier 38/38 PASS |
| NOP = 0 | PASS | run `31302792735`, job `93218216997`; NOP mean `0.000`; 30 F2P fail + 8 P2P pass |
| F2P/P2P empirical matrix | PASS | artifact `9035022133`, sha256 `66b1fa9af348179e2dddfafcfda039ac6bdec80fbbdf1e108ce961935f4738c9` |
| Leakage/package checks | PASS | environment build context excludes solution/tests/runtime state; Agent-System package isolation passed |
| FROZEN_CANDIDATE | PASS | task commit `fc137e823b43b939f7005cc598f41fe10e84e3c1` |
| Q4 Spec-Test Contract Reviewer | PENDING | packet ready: review `jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204`; `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204.packet.json` |
| Q6 Production Logic Auditor | PENDING | packet ready: review `jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564`; `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564.packet.json` |
| Quality Interlock | PENDING | requires current Q4 PASS + Q6 PASS with sufficient evidence |
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

## Q1-Q3 result

The instruction remains a short incident handoff and delegates detailed invariants to `/app/continuity/docs/continuity-contract.md`; no sentence-per-test acceptance list was introduced. It now makes clear that the task repairs the regional continuity controller while preserving the captured incident history.

Q2 added two missing F2P behaviors without exceeding the strict 30-case ceiling:
- expired lease reacquisition by the same owner id advances `fence_epoch` and invalidates the old token;
- the submitted repair leaves `/app/continuity/out/health.json` and `/app/continuity/out/reconciliation.json` describing observed durable state.

Q2 added two preservation cases:
- cleanup excludes rows newer than `journal_min_age_seconds` and explicit retention holds;
- approving a later generation does not rewrite historical event generation identity.

## Deterministic empirical evidence

PR #12 validation run `31302792735`, task job `93218216997`, artifact `9035022133`:

- Oracle: 38 collected / 38 passed / reward 1.
- NOP: 38 collected / 30 failed / 8 passed / reward 0.
- NOP failures are exactly the 30 `test_f2p_*` cases.
- NOP passes are exactly the eight `test_p2p_*` cases.
- Both new F2P cases fail against the inherited starter for their intended reason: same-owner expired lease retains the old epoch, and final report files are absent.
- Both new P2P cases pass on the inherited starter and Oracle.

The Edition-3 validation workflow later fails only at reusable AI-credential preparation because `STB_AI_API_KEY`/`STB_AI_CONFIG_B64` is not configured. Oracle/NOP completed before that dependency and remain valid deterministic freeze evidence.

## Q4/Q6 packet provenance

The repository packet generator ran successfully in GitHub Actions run `31303076913`; packet artifact `9035080063` has sha256 `84938209b155020aff59549b46bb449ccf8289f715ccc54d7f47f166e6367e0a`. The temporary workflow used only to generate those packets was removed after the exact generated packet files were committed.

### Q4

- Review ID: `jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204`
- Task commit: `fc137e823b43b939f7005cc598f41fe10e84e3c1`
- Role: `Spec-Test Contract Reviewer`
- Role contract hash: `696aa3da8960a5c5ee1b093d2b8bced4e3f95fba130883ee4afc58c846251832`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204.packet.json`
- Expected result: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-spec-test-contract-ad62d62204.json`

### Q6

- Review ID: `jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564`
- Task commit: `fc137e823b43b939f7005cc598f41fe10e84e3c1`
- Role: `Production Logic Auditor`
- Role contract hash: `d133a8d561746bb33b8622cb3e564feccfbfe669e9e601f1d0dba95762dfb29b`
- Packet: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564.packet.json`
- Expected result: `.terminus/reviews/jetstream-regional-stream-continuity/fc137e82/jetstream-regional-stream-continuity-fc137e82-production-logic-823edb7564.json`

## Current blocker

`Q4 and Q6 must now execute as independent cold packet-bound reviewers. This producer/controller execution has seen the authoring rationale and cannot self-certify either review without violating the Edition-3 independence contract.`

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `none`
- Evidence: `task deterministic gates are green; next dependency is independent semantic review`

## Next action

`Run Q4 and Q6 in separate fresh reviewer contexts using their committed generated packets. Commit each JSON result to the packet's exact review_output_path, validate packet/result freshness, and only then evaluate QUALITY_INTERLOCK_PASS. If either returns REVISE, route only its concrete findings to the responsible producer and rerun affected deterministic gates before regenerating stale review evidence.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 from merged PR #11 are authoritative.
- Keep F2P count at 30; another F2P requires consolidating/removing a genuinely duplicate case.
- Captured incident state is evidence and must not be rewritten to manufacture a healthy report.
- Current frozen task commit is `fc137e823b43b939f7005cc598f41fe10e84e3c1`.
- Q4 and Q6 are independent packet-bound reviewers; this controller execution cannot issue their PASS.
- Harbor/model credential failure happens after valid Oracle/NOP evidence and does not invalidate deterministic freeze.

## Resume rule

Resolve current task commit from Git and require `fc137e823b43b939f7005cc598f41fe10e84e3c1`. Validate the committed Q4/Q6 packet provenance, run those reviews independently, then resume at Quality Interlock aggregation.
