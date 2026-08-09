# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
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

This is a `large_system_strict` three-domain NATS JetStream continuity task. Two edge domains accept telemetry into durable journals/origin streams; a hub sources both origins, maintains the durable archive index, drives required consumers, and coordinates replay, fencing and retention. The deterministic state contains 12,000 primary telemetry events plus device, generation, archive, effect, checkpoint, replay and retention state. The private topology remains seven root-cause clusters and 26 manifestations with cross-cluster causal edges.

The merged Q1-Q8 workflow was applied after PR #10. Q1 found no verifier-only requirement that needed to be copied into the handoff. Q2 found solver-visible contract behavior that was not graded. Q3 found ambiguity between repairing the controller and rewriting captured incident state. Q7 found that a newly added verifier file was not copied into the separate verifier image. The resulting verifier now contains exactly 30 F2P scenarios and 8 P2P preservation scenarios.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | instruction plus referenced continuity contract cover the graded behaviors without hidden-test-shaped expansion; no task text was added solely from test names |
| Q2 Verifier Coverage Repair | PENDING | coverage repair authored: same-owner expired-lease fencing and final report materialization added as F2P; retention age/hold and historical generation ownership added as P2P; fresh empirical matrix required |
| Q3 Spec Ambiguity Repair | PASS | `instruction.md` now says repair the control plane while preserving captured incident history; detailed contract narrows poison/fencing/operator semantics |
| Q7 Task Format Enforcer | PENDING | verifier Dockerfile now copies `test_contract_coverage.py`; fresh Preflight/Ruff/package evidence required |
| Q5 Oracle & Runtime Repair | NOT_RUN | invoke only if fresh Oracle/runtime evidence fails |
| Creator Complexity Gate | PENDING | prior PR #10 strict complexity PASS is historical because the task tree changed |
| Production Authenticity Gate | PENDING | prior PR #10 authenticity PASS is historical because the task tree changed |
| Preflight/static | PENDING | fresh PR #12 evidence required |
| Ruff verifier | PENDING | fresh PR #12 evidence required |
| Oracle = 1 | PENDING | PR #10 run `31299220704`, job `93209204486` passed Oracle on the previous 28-F2P/6-P2P task version; current 30-F2P/8-P2P version requires rerun |
| NOP = 0 | PENDING | PR #10 run `31299220704`, job `93209204486` passed NOP on the previous task version; current version requires rerun |
| F2P/P2P empirical matrix | PENDING | target is 30 F2P starter-fail/Oracle-pass and 8 P2P preserved |
| Leakage/package checks | PENDING | fresh task package evidence required |
| FROZEN_CANDIDATE | NOT_REACHED | requires all deterministic freeze conditions on the current task commit |
| Q4 Spec-Test Contract Reviewer | PENDING | independent packet-bound review only after deterministic freeze |
| Q6 Production Logic Auditor | PENDING | independent packet-bound review only after deterministic freeze; must assess reachable non-toy production logic, not raw LOC alone |
| Quality Interlock | PENDING | requires current Q4 PASS + Q6 PASS plus completed producer/deterministic gates |
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
| Harbor LLMaJ | PENDING | after Pre-LLMaJ and Q8 diagnostic interlock |
| GPT-5.5 difficulty ×5 | NOT_RUN | official later gate |
| Claude Opus 4.8 difficulty ×5 | NOT_RUN | official later gate |
| Combined difficulty ×10 | NOT_RUN | final tier pending |
| Per-test solvability 1/10 | NOT_RUN | every verifier case must pass at least once across combined ten |
| Trial Analysis | NOT_RUN | after official trials |
| Final Compliance | PENDING | final packet-bound review |
| Final Human Quality | PENDING | final packet-bound review |
| Final package | PENDING | |

## Q1-Q3 coverage changes

- The natural handoff still delegates detailed invariants to `/app/continuity/docs/continuity-contract.md`; no sentence-per-test acceptance list was introduced.
- The handoff now distinguishes repairing the continuity controller from mutating the captured incident history.
- The detailed contract no longer promises an untested checksum construction or a blanket lease/audit rule for every recovery mutation.
- Recovery fencing now explicitly states that expiry/reacquisition advances the epoch even when the restarted worker reuses the same owner id.
- Operator-output semantics now explicitly bind `continuityctl verify` to `/app/continuity/out/health.json` and `/app/continuity/out/reconciliation.json` and prohibit manufacturing success by deleting incident evidence.

## Verifier delta

New F2P scenarios:
- expired lease reacquired by the same owner id must advance the fence epoch and invalidate the old token;
- the submitted Oracle repair must leave both requested operator JSON reports under `/app/continuity/out/`.

New P2P preservation scenarios:
- cleanup excludes both young rows and explicit retention holds even below the convergence watermark;
- approving a new origin generation does not rewrite historical event generation identity.

Private requirement/test mapping is current in `.terminus/designs/jetstream-regional-stream-continuity-test-map.json`: 24 solver-visible requirement groups, 30 F2P tests and 8 P2P tests.

## Historical deterministic evidence

PR #10 head `360fc26a9454697c0e25b4646298d79c625290b8` produced:
- Creator Complexity run `31299220688`: PASS;
- Agent System run `31299220689`: PASS;
- Production Authenticity run `31299220690`: PASS;
- Edition 3 validation run `31299220704`, JetStream job `93209204486`: Preflight PASS, Ruff PASS, Docker/install PASS, Oracle PASS, NOP PASS. The workflow failed only at reusable AI-credential preparation, so Harbor was skipped.

Those results are historical because the task changed for the Q1-Q8 pass. They are diagnostic evidence only, not current gate PASS.

## Current blocker

`Fresh PR #12 deterministic evidence is required. Q4/Q6 cannot be invoked as acceptance reviewers until the current 30-F2P/8-P2P task reaches FROZEN_CANDIDATE.`

## Root-cause classification

- Owner: `CI Orchestrator`
- Classification: `none`
- Evidence: `PR #12 current task commit fc137e823b43b939f7005cc598f41fe10e84e3c1`

## Next action

`Read PR #12 Actions for strict complexity, production authenticity, Preflight/Ruff, Oracle, NOP and empirical verifier behavior. Route any failure to Q5 or the smallest responsible producer without weakening a legitimate requirement.`

## Circuit breakers

- Status: `CLEAR`
- Trigger: `none`
- Attempts: `0`
- Required strategy change/evidence: `none`

## Decisions that must survive chat changes

- Q1-Q8 from merged PR #11 are now part of the authoritative control plane.
- Keep F2P count at 30; do not add another F2P without consolidating/removing a genuinely duplicate case.
- Captured incident state is evidence and must not be rewritten merely to make final reports green.
- Q4 and Q6 are independent packet-bound reviewers; producer work in this session cannot self-certify those gates.

## Resume rule

Resolve the current task commit from Git and inspect live PR #12 CI before changing the task. If the task tree is unchanged and deterministic gates are green, advance to `FROZEN_CANDIDATE`, then generate fresh Q4 and Q6 review packets under the merged quality-agent contracts.
