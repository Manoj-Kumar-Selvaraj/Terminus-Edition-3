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

This is a `large_system_strict` three-domain NATS JetStream continuity task. Two edge domains accept telemetry into durable journals/origin streams; a hub sources both origins, maintains the durable archive index, drives required consumers, and coordinates replay, fencing and retention. The deterministic state contains 12,000 primary telemetry events plus device, generation, archive, effect, checkpoint, replay and retention state. The private topology remains seven root-cause clusters and 26 manifestations with all 26 participating in the causal graph.

The current strict complexity run measures 5,488 substantive solver-visible runtime/configuration LOC, 26 manifestations, seven root-cause clusters, 28 causal edges, 11 cross-cluster pairs, 11 affected components, 24 mapped requirement groups, exactly 30 F2P tests and eight P2P tests.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | instruction plus referenced continuity contract cover every currently graded behavior without hidden-test-shaped expansion |
| Q2 Verifier Coverage Repair | PASS | PR #12 artifact `9035022133`: Oracle 38/38 PASS; NOP exactly 30 F2P FAIL + 8 P2P PASS; new same-owner fencing/report requirements are empirically discriminating |
| Q3 Spec Ambiguity Repair | PASS | handoff distinguishes control-plane repair from rewriting incident history; contract narrows poison/fencing/operator semantics and removes unneeded ungraded detail |
| Q7 Task Format Enforcer | PASS | run `31302792735`, job `93218216997`: Preflight, Ruff, Docker/STB install all PASS; verifier Dockerfile includes both test modules; environment `.dockerignore` excludes solution/tests/runtime state |
| Q5 Oracle & Runtime Repair | NOT_RUN | not triggered: current Oracle/runtime execution is green |
| Creator Complexity Gate | PASS | run `31302792708`, job `93218169623`: strict PASS; `substantive_loc=5488`, `tests_total=38`, `f2p=30`, `p2p=8`, `requirements=24` |
| Production Authenticity Gate | PASS | run `31302792706`, job `93218169731` PASS on current PR/task version |
| Agent System / review freshness | PASS | run `31302792712`, job `93218169903`: control-plane regressions, structure, freshness and package isolation PASS |
| Preflight/static | PASS | run `31302792735`, job `93218216997` step `Preflight` PASS |
| Ruff verifier | PASS | run `31302792735`, job `93218216997` step `Ruff verifier tests` PASS |
| Environment/verifier build | PASS | run `31302792735`, job `93218216997` step `Install stb and verify Docker` PASS |
| Oracle = 1 | PASS | run `31302792735`, job `93218216997`; Harbor utility Oracle mean `1.000`; verifier `38 passed in 3.83s` |
| NOP = 0 | PASS | run `31302792735`, job `93218216997`; Harbor utility NOP mean `0.000`; verifier `30 failed, 8 passed in 4.01s` |
| F2P/P2P empirical matrix | PASS | artifact `9035022133` (`sha256:66b1fa9af348179e2dddfafcfda039ac6bdec80fbbdf1e108ce961935f4738c9`): all 30 F2P Oracle-pass/starter-fail; all 8 P2P pass in both |
| Leakage/package checks | PASS | current environment build context copies only `environment/continuity/`; `.dockerignore` excludes `solution/`, `tests/`, state/output/runtime caches; Agent-System package-isolation PASS |
| FROZEN_CANDIDATE | PASS | current task commit `fc137e823b43b939f7005cc598f41fe10e84e3c1`; all deterministic freeze conditions above are current |
| Q4 Spec-Test Contract Reviewer | PENDING | next mandatory independent packet-bound review |
| Q6 Production Logic Auditor | PENDING | next mandatory independent packet-bound review; must judge reachability/coupling/toy-padding independently of numeric complexity PASS |
| Quality Interlock | PENDING | requires current Q4 PASS + Q6 PASS with sufficient evidence |
| Task Architect | PENDING | normal cold Stage-B review after quality interlock |
| Verifier Engineer | PENDING | normal cold Stage-B review after quality interlock |
| Originality & Authenticity | PENDING | normal cold Stage-B review after quality interlock |
| Difficulty design | PENDING | normal cold Stage-B review after quality interlock |
| Compliance pre-review | PENDING | normal cold Stage-B review after quality interlock |
| Instruction Reviewer | PENDING | normal cold Stage-B review after quality interlock |
| Documentation Reviewer | PENDING | normal cold Stage-B review after quality interlock |
| Comprehensive Reviewer | PENDING | after specialist reports; checklist coverage must be 100% |
| Pre-LLMaJ aggregate | PENDING | requires current specialist + comprehensive evidence |
| Q8 GPT Perspective | PENDING | isolated diagnostic solve after Pre-LLMaJ PASS; not official model evidence |
| Q8 Claude Perspective | PENDING | isolated diagnostic solve after Pre-LLMaJ PASS; not official model evidence |
| Harbor LLMaJ | PENDING | current CI credential step is unavailable; Harbor remains downstream of Pre-LLMaJ/Q8 under the control-plane order |
| GPT-5.5 difficulty ×5 | NOT_RUN | official later gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | official later gate |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | every verifier case must pass at least once across combined ten |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | |

## Q1-Q3 result

The instruction remains a short incident handoff and delegates detail to `/app/continuity/docs/continuity-contract.md`; no one-sentence-per-test acceptance list was introduced. It now makes clear that the task repairs the regional continuity controller while preserving the captured incident history. The detailed contract explicitly covers stable event authority, origin generation, source-only archive topology, crash-safe effect/checkpoint/ack behavior, identity reconciliation, missing-only replay, fenced recovery and convergence-bounded retention.

Q2 added two missing F2P behaviors without exceeding the strict 30-case ceiling:
- expired lease reacquisition by the same owner id advances `fence_epoch` and invalidates the old token;
- the submitted repair leaves `/app/continuity/out/health.json` and `/app/continuity/out/reconciliation.json` describing observed durable state.

Q2 also added two preservation cases:
- cleanup excludes rows newer than `journal_min_age_seconds` and explicit retention holds;
- approving a later generation does not rewrite historical event generation identity.

## Deterministic empirical evidence

PR #12 validation run `31302792735`, task job `93218216997`, artifact `9035022133`:

- Oracle: 38 collected / 38 passed / reward 1.
- NOP: 38 collected / 30 failed / 8 passed / reward 0.
- NOP failures are exactly the 30 `test_f2p_*` cases.
- NOP passes are exactly the eight `test_p2p_*` cases.
- Both new F2P cases fail against the inherited starter for their intended reason: same-owner expired lease remains epoch 1, and final report files are absent.
- Both new P2P cases pass on the inherited starter and Oracle.

The overall Edition-3 workflow conclusion is red only because the later reusable-AI-credential preparation step has no `STB_AI_API_KEY`/`STB_AI_CONFIG_B64`; Oracle/NOP completed before that infrastructure dependency and are valid deterministic evidence.

## Current blocker

`Independent Q4 Spec-Test Contract Reviewer and Q6 Production Logic Auditor have not yet run. Producer work in this controller cannot self-certify those quality-interlock gates.`

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `none`
- Evidence: `deterministic task gates are green; downstream reusable-AI credential is an external dependency, not a task defect`

## Next action

`Generate fresh v3 context packets for Q4 spec-test-contract and Q6 production-logic against task commit fc137e823b43b939f7005cc598f41fe10e84e3c1. Run those roles cold and independently. Do not begin ordinary Pre-LLMaJ Stage-B until both quality reviews pass with sufficient evidence.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 from merged PR #11 are authoritative.
- Keep F2P count at 30; another F2P requires consolidating/removing a genuinely duplicate case.
- Captured incident state is evidence and is not rewritten to manufacture a healthy report.
- Current frozen task commit is `fc137e823b43b939f7005cc598f41fe10e84e3c1`.
- Q4 and Q6 are independent packet-bound reviewers; this producer/controller session cannot issue their acceptance PASS.
- Harbor/model credential failure occurs after valid Oracle/NOP evidence and does not invalidate deterministic freeze.

## Resume rule

Resolve the task commit from Git and require `fc137e823b43b939f7005cc598f41fe10e84e3c1`. Verify the cited PR #12 runs/artifact are still current, then resume with generated Q4/Q6 packet-bound reviews. If either returns REVISE, route only its concrete findings to the appropriate producer and rerun affected deterministic gates before regenerating the stale quality review.
