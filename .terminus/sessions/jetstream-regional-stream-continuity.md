# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `c21c6e2f439d558c679b6f8e4a7977e8a2b014bd`
- Agent-system policy: `2.3`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.1`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`

## Current task profile

The task remains the `large_system_strict` three-domain NATS JetStream regional-continuity scenario. Third-cycle Q4 remediation preserves the 40-test shape at exactly 30 F2P + 10 P2P across 26 mapped requirements. Solver-visible substantive runtime/configuration is now 5,523 LOC: the prior 5,488 plus the reconciliation progress interface required by the existing solver-visible contract. Formatting-only churn from the first remediation helper was removed before this task commit.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | Existing solver-visible continuity requirements remain the authority; no requirement was weakened or expanded into a hidden-test checklist. |
| Q2 Verifier Coverage Repair | FIX_APPLIED_PENDING_RERUN | Q4 findings Q4-01/Q4-03/Q4-04/Q4-05/Q4-06 and the verifier side of Q4-02 were remediated in existing tests; suite remains 30 F2P + 10 P2P. |
| Q3 Spec Ambiguity Repair | PASS | Q4 reported evidence sufficient; remediation preserves natural solver-visible wording and removes undocumented diagnostic-literal dependencies. |
| Q5 Oracle & Runtime Repair | FIX_APPLIED_PENDING_RERUN | Q4-02 required the already-promised reconciliation outputs to be surfaced by `ReconciliationSummary` and populated in starter/reference paths. |
| Q7 Task Format Enforcer | PENDING_FRESH_EVIDENCE | Require fresh Preflight/Ruff/build/package evidence for task commit `c21c6e2...`. |
| Creator Complexity Gate | PASS | run `31315624734`, job `93250274880`; 5,523 substantive LOC / 40 tests / 30 F2P / 10 P2P / 26 requirements. |
| Production Authenticity Gate | PENDING_RERUN | Exact cleaned task commit changed; require current clean-head evidence. |
| Agent System / review freshness | PENDING_RERUN | Session is now rebound to current task commit and historical Q4/Q6 are marked stale. |
| Preflight/static | PENDING | Fresh Edition-3 run required. |
| Ruff verifier | PENDING | Fresh Edition-3 run required. |
| Environment/verifier build | PENDING | Fresh Edition-3 run required. |
| Oracle = 1 | PENDING | Target 40/40 PASS on current task commit. |
| NOP = 0 | PENDING | Target exactly 30 F2P FAIL + 10 P2P PASS on current task commit. |
| F2P/P2P empirical matrix | PENDING | Require fresh current-task evidence. |
| Leakage/package checks | PENDING_FRESH_EVIDENCE | Require clean-head Agent-System/package-isolation evidence. |
| FROZEN_CANDIDATE | NOT_REACHED | Older freezes are stale after the third-cycle Q4 remediation. |
| Q4 Spec-Test Contract Reviewer | STALE_REVISE | `c3ee2778` review `jetstream-regional-stream-continuity-c3ee2778-spec-test-contract-8075aa9028` returned REVISE/HIGH/SUFFICIENT and drove this repair. |
| Q6 Production Logic Auditor | STALE_PASS | `c3ee2778` Q6 PASS/HIGH/SUFFICIENT is retained only as history; exact task-commit provenance moved. |
| Quality Interlock | PENDING | Requires deterministic refreeze and fresh packet-bound Q4 + Q6 PASS. |
| Task Architect | PENDING | after Quality Interlock |
| Verifier Engineer | PENDING | after Quality Interlock |
| Originality & Authenticity | PENDING | after Quality Interlock |
| Difficulty design | PENDING | after Quality Interlock |
| Compliance pre-review | PENDING | after Quality Interlock |
| Instruction Reviewer | PENDING | after Quality Interlock |
| Documentation Reviewer | PENDING | after Quality Interlock |
| Comprehensive Reviewer | PENDING | after Stage-B specialists |
| Pre-LLMaJ aggregate | PENDING | after specialist and Comprehensive reviews |
| Q8 GPT Perspective Simulation | PENDING | after Pre-LLMaJ PASS |
| Q8 Claude Perspective Simulation | PENDING | after Pre-LLMaJ PASS |
| Harbor LLMaJ | PENDING | later gate; reusable AI credentials are independent of deterministic validation |
| GPT-5.5 difficulty ×5 | NOT_RUN | later official gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | later official gate |
| Combined difficulty ×10 | NOT_RUN | later official gate |
| Per-test solvability 1/10 | NOT_RUN | later official gate |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | after all required gates |

## Third-cycle Q4 remediation

Independent Q4 on `c3ee277828c2a156ecce9d335820d57b9fd2a0e0` returned `REVISE/HIGH/SUFFICIENT` with six findings. The current task version addresses them without increasing F2P count or expanding `instruction.md`:

1. Tests no longer depend on undocumented publish/reconciliation diagnostic label strings; they grade observable state and event-linked findings.
2. The existing reconciliation contract's promised highest contiguous archive-origin progress and required-consumer progress are now explicit `ReconciliationSummary` outputs, populated by shared/starter/reference paths and graded behaviorally.
3. Poison quarantine now proves a QUARANTINED audit effect, no confirmed business dispatch, and unchanged application/ack checkpoints.
4. Same-owner stale-epoch renewal is rejected without mutating the current lease.
5. Completing the real west replay is followed by retention recomputation proving terminal replay state no longer pins cleanup.
6. Final report verification derives grading-critical expectations directly from SQLite durable state rather than calling the submitted engine as its own oracle.

The initial remediation commit `d6a2cd9fdb61f37be7d59f004875c0991218d02c` also contained formatter churn. Commit `c21c6e2f439d558c679b6f8e4a7977e8a2b014bd` removes that churn while preserving the semantic repair. Strict validation of the cleaned tree reports 5,523 substantive LOC and 40 = 30 F2P + 10 P2P.

## Historical provenance

- `fc137e82...`: Q4 REVISE; Q6 PASS.
- `a57ed7e6...`: Q4 REVISE; Q6 PASS.
- `c3ee2778...`: Q4 REVISE/HIGH/SUFFICIENT; Q6 PASS/HIGH/SUFFICIENT; both stale after current task changes.
- `c3ee2778...` deterministic artifact `9037758650`: Oracle 40/40 and NOP 30 F2P FAIL + 10 P2P PASS; stale after current task changes.

## Current blocker

Run fresh deterministic validation on task commit `c21c6e2f439d558c679b6f8e4a7977e8a2b014bd`. Require strict gates, Preflight/Ruff/build, Oracle=1, NOP=0, Oracle 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS. Do not refreeze on partial evidence.

## Next action

Inspect live PR #12 Actions on the session-reconciled head. If the exact current task version passes deterministic validation and strict/authenticity/freshness gates, restore `FROZEN_CANDIDATE`, generate new repository-native Q4/Q6 packets, remove the packet helper, and rerun both reviewers independently in cold contexts.
